const { ipcRenderer } = require('electron');

// ---------------------------------------------------------------------------
// NDI frame capture — preload script
// ---------------------------------------------------------------------------
// With contextIsolation disabled, this script shares the page's global scope.
// Sets window.ndiEnabled BEFORE the page scripts run so the renderer can
// adjust pixelRatio and preserveDrawingBuffer accordingly.

const NDI_WIDTH = 1920;
const NDI_HEIGHT = 1080;
const FRAME_INTERVAL_MS = 1000 / 30; // ~33.3ms for 30fps

// Set BEFORE page scripts run — renderer checks this for pixelRatio & preserveDrawingBuffer
window.ndiEnabled = true;

// ---------------------------------------------------------------------------
// Force the renderer viewport to fill the Electron window so the canvas
// is exactly 1920×1080. The normal browser UI uses 80vw × 80vh with borders.
// HUD overlay stays visible for monitoring.
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  const style = document.createElement('style');
  style.textContent = `
    #viewport {
      left: 0 !important;
      top: 0 !important;
      transform: none !important;
      width: 100vw !important;
      height: 100vh !important;
      border: none !important;
      border-radius: 0 !important;
      box-shadow: none !important;
    }
    #resize-handle { display: none !important; }
  `;
  document.head.appendChild(style);

  let lastCaptureTime = 0;

  function waitForRenderer() {
    if (window.__voiceMeshRenderer) {
      // Trigger resize so the renderer picks up the new 100vw×100vh viewport
      window.dispatchEvent(new Event('resize'));
      startCapture();
    } else {
      setTimeout(waitForRenderer, 100);
    }
  }

  function startCapture() {
    const threeRenderer = window.__voiceMeshRenderer;
    const gl = threeRenderer.getContext();

    const pixelBuffer = new Uint8Array(NDI_WIDTH * NDI_HEIGHT * 4);
    const rowBuffer = new Uint8Array(NDI_WIDTH * 4);

    console.log('[NDI] Frame capture started (30fps)');

    const originalRAF = window.requestAnimationFrame;
    window.requestAnimationFrame = function (callback) {
      return originalRAF.call(window, (timestamp) => {
        callback(timestamp);

        const now = performance.now();
        if (now - lastCaptureTime < FRAME_INTERVAL_MS) return;
        lastCaptureTime = now;

        try {
          gl.readPixels(0, 0, NDI_WIDTH, NDI_HEIGHT, gl.RGBA, gl.UNSIGNED_BYTE, pixelBuffer);

          // WebGL readPixels returns bottom-up rows; NDI expects top-down.
          const stride = NDI_WIDTH * 4;
          for (let y = 0; y < NDI_HEIGHT / 2; y++) {
            const topOffset = y * stride;
            const bottomOffset = (NDI_HEIGHT - 1 - y) * stride;

            rowBuffer.set(pixelBuffer.subarray(topOffset, topOffset + stride));
            pixelBuffer.copyWithin(topOffset, bottomOffset, bottomOffset + stride);
            pixelBuffer.set(rowBuffer, bottomOffset);
          }

          ipcRenderer.send('ndi:frame', pixelBuffer.buffer);
        } catch (err) {
          if (!startCapture._errLogged) {
            console.error('[NDI] Frame capture error:', err.message);
            startCapture._errLogged = true;
          }
        }
      });
    };
  }

  waitForRenderer();
});
