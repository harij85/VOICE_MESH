const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow = null;
let ndiProcess = null;

const NDI_WIDTH = 1920;
const NDI_HEIGHT = 1080;
const FRAME_SIZE = NDI_WIDTH * NDI_HEIGHT * 4; // RGBA

// Determine renderer URL: --dev flag uses Vite dev server, otherwise built files
const isDev = process.argv.includes('--dev');
const RENDERER_URL = isDev
  ? 'http://localhost:5173'
  : `file://${path.join(__dirname, '..', 'renderer', 'dist', 'index.html')}`;

function startNDISender() {
  const senderScript = path.join(__dirname, 'ndi_sender.py');

  // Try the BRAIN venv Python first, then fall back to system python
  const venvPython = path.join(__dirname, '..', 'BRAIN', '.venv', 'bin', 'python');
  const pythonCmd = require('fs').existsSync(venvPython) ? venvPython : 'python3';

  ndiProcess = spawn(pythonCmd, [
    senderScript,
    '--name', 'VOICE_MESH',
    '--width', String(NDI_WIDTH),
    '--height', String(NDI_HEIGHT),
  ], {
    stdio: ['pipe', 'inherit', 'inherit'],
  });

  ndiProcess.on('error', (err) => {
    console.error('[NDI] Failed to start sender subprocess:', err.message);
    ndiProcess = null;
  });

  ndiProcess.on('exit', (code) => {
    console.log(`[NDI] Sender process exited with code ${code}`);
    ndiProcess = null;
  });

  console.log(`[NDI] Sender subprocess started (PID: ${ndiProcess.pid})`);
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: NDI_WIDTH,
    height: NDI_HEIGHT,
    useContentSize: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: false,
      nodeIntegration: false,
    },
    // Hardware-accelerated window (NOT offscreen — offscreen disables GPU)
    backgroundColor: '#00000000',
  });

  mainWindow.loadURL(RENDERER_URL);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  console.log(`[NDI] Loading renderer from: ${RENDERER_URL}`);
}

app.whenReady().then(() => {
  startNDISender();
  createWindow();

  // Listen for RGBA frame data from the renderer process
  ipcMain.on('ndi:frame', (_event, buffer) => {
    if (!ndiProcess || !ndiProcess.stdin.writable) return;

    try {
      // Write raw RGBA bytes to the Python sender's stdin
      const buf = Buffer.from(buffer);
      if (buf.length === FRAME_SIZE) {
        ndiProcess.stdin.write(buf);
      }
    } catch (err) {
      // Pipe may be closed if the sender exited
    }
  });
});

app.on('window-all-closed', () => {
  if (ndiProcess) {
    try {
      ndiProcess.stdin.end();
      ndiProcess.kill('SIGTERM');
    } catch (e) {
      // Ignore cleanup errors
    }
  }
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
