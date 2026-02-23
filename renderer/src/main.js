import * as THREE from "three";
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader.js';
import { createWsClient } from "./wsClient.js";
import { DEFAULT_SCENE, mergeScene } from "./sceneSpec.js";
import { createComposer, updateEffects, updateComposerSize } from "./postProcessing.js";
import vertSrc from "./shaders/passthrough.vert.glsl?raw";
import fragSrc from "./shaders/raymarch.frag.glsl?raw";
import enhanceVertSrc from "./shaders/meshEnhance.vert.glsl?raw";
import enhanceFragSrc from "./shaders/meshEnhance.frag.glsl?raw";

// Maps scene spec primitive names to the u_shapeType float the shader expects
const SHAPE_TYPE = {
  rounded_box:  0,
  rounded_slab: 0, // treated as rounded_box in shader
  cylinder:     1,
  sphere:       2,
  capsule:      3,
  torus:        4,
};

// Shared uniforms object — values are updated by syncRaymarchUniforms()
const raymarchUniforms = {
  u_time:            { value: 0.0 },
  u_resolution:      { value: new THREE.Vector2(1, 1) },
  u_color:           { value: new THREE.Color("#4b7bff") },
  u_roughness:       { value: 0.35 },
  u_distance:        { value: 2.2 },
  u_orbit:           { value: 1.0 },
  u_cameraAngle:     { value: 0.0 },
  u_cameraElevation: { value: 0.0 },
  u_shapeType:       { value: 0.0 },
  u_outline:         { value: 0.12 },
  u_bloom:           { value: 0.15 },
  u_alpha:           { value: 1.0 },
};

// Shared uniforms for the enhanced Shap-E mesh material
const enhanceUniforms = {
  u_color:        { value: new THREE.Color("#4b7bff") },
  u_roughness:    { value: 0.35 },
  u_alpha:        { value: 1.0 },
  u_rimIntensity: { value: 0.0 },
  u_rimColor:     { value: new THREE.Color("#ffffff") },
  u_envReflect:   { value: 0.0 },
};

// Lazy-created singleton — avoids create/dispose churn on every command
let enhancedMaterial = null;

function getEnhancedMaterial() {
  if (!enhancedMaterial) {
    enhancedMaterial = new THREE.ShaderMaterial({
      vertexShader:   enhanceVertSrc,
      fragmentShader: enhanceFragSrc,
      uniforms:       enhanceUniforms,
      transparent:    true,
      side:           THREE.FrontSide,
    });
  }
  return enhancedMaterial;
}

function syncEnhanceUniforms() {
  enhanceUniforms.u_color.value.set(sceneSpec.material.color);
  enhanceUniforms.u_roughness.value    = sceneSpec.material.roughness ?? 0.35;
  enhanceUniforms.u_alpha.value        = sceneSpec.fx.alpha ?? 1.0;
  enhanceUniforms.u_rimIntensity.value = sceneSpec.fx.rim ?? 0.0;
  enhanceUniforms.u_envReflect.value   = sceneSpec.fx.env_reflect ?? 0.0;
}

function needsEnhancedMaterial() {
  return (sceneSpec.fx.rim ?? 0) > 0 || (sceneSpec.fx.env_reflect ?? 0) > 0;
}

const hud = document.getElementById("hud");
const viewport = document.getElementById("viewport");
const resizeHandle = document.getElementById("resize-handle");

let sceneSpec = structuredClone(DEFAULT_SCENE);

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  premultipliedAlpha: false,   // straight alpha for clean D3/NDI compositing
  preserveDrawingBuffer: !!window.ndiEnabled, // keep pixels for NDI readPixels capture
  powerPreference: "high-performance"
});
// In NDI mode, use pixelRatio 1 so GL framebuffer matches 1920×1080 exactly
renderer.setPixelRatio(window.ndiEnabled ? 1 : Math.min(devicePixelRatio, 2));
renderer.setClearColor(0x000000, 0);

viewport.appendChild(renderer.domElement);

const scene = new THREE.Scene();

// Perspective camera for proper 3D rendering
const camera = new THREE.PerspectiveCamera(
  sceneSpec.camera.fov || 35,
  1, // aspect ratio updated in resize()
  0.1,
  100
);

// Position camera based on scene spec and sync shader camera uniforms
function updateCameraPosition() {
  const distance = sceneSpec.camera.distance;
  const angle = cameraAngle;
  const elevation = cameraElevation;

  // Keep Three.js camera in sync for Shap-E mesh rendering
  camera.position.x = distance * Math.cos(elevation) * Math.sin(angle);
  camera.position.y = distance * Math.sin(elevation);
  camera.position.z = distance * Math.cos(elevation) * Math.cos(angle);
  camera.lookAt(0, 0, 0);

  // Sync raymarching shader camera uniforms
  raymarchUniforms.u_distance.value     = distance;
  raymarchUniforms.u_cameraAngle.value  = angle;
  raymarchUniforms.u_cameraElevation.value = elevation;
}

// Lighting setup
const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
scene.add(ambientLight);

const directionalLight = new THREE.DirectionalLight(0xffffff, 1.2);
directionalLight.position.set(5, 5, 5);
directionalLight.castShadow = true;
scene.add(directionalLight);

// Key light (softer, from side)
const keyLight = new THREE.DirectionalLight(0xffffff, 0.6);
keyLight.position.set(-3, 2, 4);
scene.add(keyLight);

// Current mesh reference (for disposal)
let currentMesh = null;

const plyLoader = new PLYLoader();

async function loadExternalMesh(url) {
  return new Promise((resolve, reject) => {
    plyLoader.load(url, geometry => {
      // Centre geometry at origin
      geometry.computeBoundingBox();
      const centre = new THREE.Vector3();
      geometry.boundingBox.getCenter(centre);
      geometry.translate(-centre.x, -centre.y, -centre.z);

      // Normalise scale so largest extent = 1
      geometry.computeBoundingBox();
      const size = new THREE.Vector3();
      geometry.boundingBox.getSize(size);
      const maxDim = Math.max(size.x, size.y, size.z);
      geometry.scale(1.0 / maxDim, 1.0 / maxDim, 1.0 / maxDim);

      // Remove Shap-E vertex colours — let material.color drive appearance
      geometry.deleteAttribute('color');

      // Shap-E PLY files don't include vertex normals.  Compute them so
      // both MeshStandardMaterial and the enhanced ShaderMaterial get
      // correct lighting and Fresnel calculations.
      if (!geometry.hasAttribute('normal')) {
        geometry.computeVertexNormals();
      }

      resolve(geometry);
    }, undefined, reject);
  });
}

/**
 * Creates a fullscreen raymarching quad using the GLSL SDF shader.
 * The shader manages its own camera, lighting, and shape via uniforms.
 * CRITICAL: Disposes old geometry/material to prevent memory leaks.
 */
function updateMesh() {
  if (currentMesh) {
    scene.remove(currentMesh);
    if (currentMesh.geometry) currentMesh.geometry.dispose();
    if (currentMesh.material && currentMesh.material !== enhancedMaterial) {
      currentMesh.material.dispose();
    }
  }

  // PlaneGeometry(2, 2) → vertices at (±1, ±1, 0) in clip space.
  // RawShaderMaterial passes them directly without matrix transforms,
  // so the quad covers the entire screen regardless of camera position.
  const geometry = new THREE.PlaneGeometry(2, 2);
  const material = new THREE.RawShaderMaterial({
    vertexShader:   vertSrc,
    fragmentShader: fragSrc,
    uniforms:       raymarchUniforms,
    transparent:    true,
    depthTest:      false,
    depthWrite:     false,
  });

  currentMesh = new THREE.Mesh(geometry, material);
  currentMesh.frustumCulled = false; // clip-space quad would be culled otherwise
  scene.add(currentMesh);
}

/**
 * Pushes the current sceneSpec values into the raymarching shader uniforms.
 * Call whenever sceneSpec changes and the raymarching quad is active.
 */
function syncRaymarchUniforms() {
  const primitive = sceneSpec.shape_hint?.primitive || 'rounded_box';
  raymarchUniforms.u_shapeType.value   = SHAPE_TYPE[primitive] ?? 0;
  raymarchUniforms.u_color.value.set(sceneSpec.material.color);
  raymarchUniforms.u_roughness.value   = sceneSpec.material.roughness ?? 0.35;
  raymarchUniforms.u_orbit.value       = sceneSpec.camera.orbit ? 1.0 : 0.0;
  raymarchUniforms.u_outline.value     = sceneSpec.fx.outline ?? 0.12;
  raymarchUniforms.u_bloom.value       = sceneSpec.fx.bloom   ?? 0.15;
  raymarchUniforms.u_alpha.value       = sceneSpec.fx.alpha   ?? 1.0;
  // camera position uniforms are kept current by updateCameraPosition()
}

// Initialize with default mesh
updateMesh();

// Initialize post-processing composer
const passes = createComposer(renderer, scene, camera);
const { composer } = passes;

// Expose internals for NDI frame capture (only used inside Electron wrapper)
window.__voiceMeshRenderer = renderer;
window.__voiceMeshPasses = passes;
window.__voiceMeshComposer = composer;

// Mouse camera controls
let mouseDown = false;
let lastMouseX = 0;
let lastMouseY = 0;
let cameraAngle = 0;
let cameraElevation = 0;

renderer.domElement.addEventListener("mousedown", (e) => {
  mouseDown = true;
  lastMouseX = e.clientX;
  lastMouseY = e.clientY;
});

window.addEventListener("mouseup", () => {
  mouseDown = false;
});

window.addEventListener("mousemove", (e) => {
  if (mouseDown) {
    const deltaX = e.clientX - lastMouseX;
    const deltaY = e.clientY - lastMouseY;

    cameraAngle -= deltaX * 0.01;
    cameraElevation += deltaY * 0.01;
    cameraElevation = Math.max(-Math.PI / 2 + 0.1, Math.min(Math.PI / 2 - 0.1, cameraElevation));

    updateCameraPosition();

    lastMouseX = e.clientX;
    lastMouseY = e.clientY;
  }
});

renderer.domElement.addEventListener("wheel", (e) => {
  e.preventDefault();
  const zoomSpeed = 0.001;
  sceneSpec.camera.distance += e.deltaY * zoomSpeed;
  sceneSpec.camera.distance = Math.max(0.8, Math.min(8.0, sceneSpec.camera.distance));
  updateCameraPosition();
});

// Viewport drag functionality
let isDraggingViewport = false;
let dragOffsetX = 0;
let dragOffsetY = 0;

viewport.addEventListener("mousedown", (e) => {
  if (e.target === viewport || e.target.tagName === 'CANVAS') {
    const rect = viewport.getBoundingClientRect();
    const isNearEdge = e.clientX > rect.right - 30 || e.clientY > rect.bottom - 30;

    if (!isNearEdge && !mouseDown) {
      isDraggingViewport = true;
      const transform = window.getComputedStyle(viewport).transform;
      const matrix = new DOMMatrix(transform);
      dragOffsetX = e.clientX - matrix.m41;
      dragOffsetY = e.clientY - matrix.m42;
      viewport.style.cursor = 'grabbing';
    }
  }
});

window.addEventListener("mousemove", (e) => {
  if (isDraggingViewport) {
    const newX = e.clientX - dragOffsetX;
    const newY = e.clientY - dragOffsetY;
    viewport.style.transform = `translate(${newX}px, ${newY}px)`;
  }
});

window.addEventListener("mouseup", () => {
  if (isDraggingViewport) {
    isDraggingViewport = false;
    viewport.style.cursor = 'move';
  }
});

// Viewport resize functionality
let isResizing = false;
let resizeStartX = 0;
let resizeStartY = 0;
let resizeStartWidth = 0;
let resizeStartHeight = 0;

resizeHandle.addEventListener("mousedown", (e) => {
  e.stopPropagation();
  isResizing = true;
  resizeStartX = e.clientX;
  resizeStartY = e.clientY;
  const rect = viewport.getBoundingClientRect();
  resizeStartWidth = rect.width;
  resizeStartHeight = rect.height;
});

window.addEventListener("mousemove", (e) => {
  if (isResizing) {
    const deltaX = e.clientX - resizeStartX;
    const deltaY = e.clientY - resizeStartY;
    const newWidth = Math.max(300, resizeStartWidth + deltaX);
    const newHeight = Math.max(200, resizeStartHeight + deltaY);

    viewport.style.width = `${newWidth}px`;
    viewport.style.height = `${newHeight}px`;

    resize();
  }
});

window.addEventListener("mouseup", () => {
  isResizing = false;
});

// Control buttons
document.getElementById("reset-view").addEventListener("click", () => {
  viewport.style.transform = "translate(-50%, -50%)";
  viewport.style.left = "50%";
  viewport.style.top = "50%";
  viewport.style.width = "80vw";
  viewport.style.height = "80vh";
  cameraAngle = 0;
  cameraElevation = 0;
  sceneSpec.camera.distance = 2.2;
  updateCameraPosition();
  resize();
});

document.getElementById("fullscreen").addEventListener("click", () => {
  if (!document.fullscreenElement) {
    viewport.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
});

function resize() {
  const rect = viewport.getBoundingClientRect();
  renderer.setSize(rect.width, rect.height);
  camera.aspect = rect.width / rect.height;
  camera.updateProjectionMatrix();
  updateComposerSize(passes, rect.width, rect.height, renderer.getPixelRatio());

  // Keep u_resolution in sync so the shader can convert gl_FragCoord to UVs
  const pr = renderer.getPixelRatio();
  raymarchUniforms.u_resolution.value.set(rect.width * pr, rect.height * pr);
}
window.addEventListener("resize", resize);
resize();

const clock = new THREE.Clock();

async function applySceneSpec(next) {
  const prev = sceneSpec;
  sceneSpec = mergeScene(sceneSpec, next);

  const isRaymarchActive = currentMesh?.material instanceof THREE.RawShaderMaterial;

  if (!sceneSpec.mesh_url) {
    // ── Raymarching mode ──────────────────────────────────────────────────
    // Ensure a fullscreen raymarching quad is in the scene (it may have been
    // replaced by a Shap-E PLY mesh on a previous command).
    if (!isRaymarchActive) {
      updateMesh();
    }
    syncRaymarchUniforms();

  } else if (sceneSpec.mesh_url !== prev.mesh_url) {
    // ── Shap-E mesh swap — new URL arrived ───────────────────────────────
    try {
      const geometry = await loadExternalMesh(sceneSpec.mesh_url);
      const material = new THREE.MeshStandardMaterial({
        color:     new THREE.Color(sceneSpec.material.color),
        roughness: sceneSpec.material.roughness ?? 0.35,
        metalness: 0.1,
        transparent: true,
        opacity:   sceneSpec.fx.alpha ?? 1.0,
        side:      THREE.FrontSide,
      });
      if (currentMesh) {
        scene.remove(currentMesh);
        currentMesh.geometry.dispose();
        // Don't dispose the shared enhanced singleton
        if (currentMesh.material !== enhancedMaterial) {
          currentMesh.material.dispose();
        }
      }
      if (needsEnhancedMaterial()) {
        syncEnhanceUniforms();
        currentMesh = new THREE.Mesh(geometry, getEnhancedMaterial());
      } else {
        currentMesh = new THREE.Mesh(geometry, material);
      }
      scene.add(currentMesh);
      updateEffects(passes, sceneSpec, currentMesh);
    } catch (e) {
      console.warn('PLY load failed, keeping current mesh:', e);
    }

  } else if (sceneSpec.mesh_url && !isRaymarchActive && currentMesh?.material) {
    // ── Shap-E mesh active — keep material in sync with voice commands ────
    if (needsEnhancedMaterial()) {
      // Swap to enhanced ShaderMaterial if not already using it
      if (!(currentMesh.material instanceof THREE.ShaderMaterial)) {
        // Dispose the old MeshStandardMaterial (but never the shared singleton)
        currentMesh.material.dispose();
        currentMesh.material = getEnhancedMaterial();
      }
      syncEnhanceUniforms();
    } else {
      // Swap back to MeshStandardMaterial if currently using enhanced
      if (currentMesh.material instanceof THREE.ShaderMaterial) {
        // Don't dispose — it's the shared singleton
        currentMesh.material = new THREE.MeshStandardMaterial({
          color:       new THREE.Color(sceneSpec.material.color),
          roughness:   sceneSpec.material.roughness ?? 0.35,
          metalness:   0.1,
          transparent: true,
          opacity:     sceneSpec.fx.alpha ?? 1.0,
          side:        THREE.FrontSide,
        });
      } else {
        currentMesh.material.color.set(sceneSpec.material.color);
        currentMesh.material.roughness = sceneSpec.material.roughness ?? 0.35;
        currentMesh.material.opacity   = sceneSpec.fx.alpha ?? 1.0;
      }
    }
  }

  // Camera (updates both Three.js camera and shader uniforms)
  updateCameraPosition();
  camera.fov = sceneSpec.camera.fov || 35;
  camera.updateProjectionMatrix();

  // Post-processing bloom (outline pass is disabled in raymarch mode — the
  // shader handles rim lighting via u_outline internally)
  updateEffects(passes, sceneSpec, isRaymarchActive ? null : currentMesh);

  hud.textContent =
`WS: connected
Object: ${sceneSpec.object.name} (${sceneSpec.object.category})
Primitive: ${sceneSpec.shape_hint?.primitive || 'rounded_box'}
Style: ${sceneSpec.presentation.style}
Material: ${sceneSpec.material.preset} ${sceneSpec.material.color}
Camera: ${sceneSpec.camera.orbit ? "orbit" : "static"} dist=${sceneSpec.camera.distance.toFixed(2)}
FX: outline=${sceneSpec.fx.outline.toFixed(2)} bloom=${sceneSpec.fx.bloom.toFixed(2)} alpha=${sceneSpec.fx.alpha.toFixed(2)} rim=${(sceneSpec.fx.rim ?? 0).toFixed(2)} env=${(sceneSpec.fx.env_reflect ?? 0).toFixed(2)}
Shap-E: ${sceneSpec.generating ? "generating\u2026" : sceneSpec.mesh_url ? "mesh loaded" : "\u2014"}`;
}

const ws = createWsClient({
  url: `ws://${location.hostname}:8765`,
  onScene: (s) => applySceneSpec(s),
  onStatus: (t) => (hud.textContent = t)
});

// Handy: type commands with keyboard (demo fallback)
// Uses an in-page input bar instead of window.prompt() which fails in Electron.
const commandBar = document.getElementById("command-bar");
const commandInput = document.getElementById("command-input");

function openCommandBar() {
  commandBar.style.display = "block";
  commandInput.value = "";
  commandInput.focus();
}

function closeCommandBar() {
  commandBar.style.display = "none";
  commandInput.blur();
}

window.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && commandBar.style.display === "none") {
    e.preventDefault();
    openCommandBar();
  } else if (e.key === "Escape") {
    closeCommandBar();
  }
});

commandInput.addEventListener("keydown", (e) => {
  e.stopPropagation(); // prevent outer Enter handler from re-triggering
  if (e.key === "Enter") {
    const text = commandInput.value.trim();
    closeCommandBar();
    if (text) ws.sendCommand(text);
  } else if (e.key === "Escape") {
    closeCommandBar();
  }
});

// Auto-rotation when orbit is enabled
let autoRotationAngle = 0;

function animate() {
  const delta = clock.getDelta();
  raymarchUniforms.u_time.value = clock.elapsedTime;

  // Auto-orbit if enabled
  if (sceneSpec.camera.orbit && !mouseDown) {
    autoRotationAngle += delta * 0.3;
    cameraAngle = autoRotationAngle;
    updateCameraPosition();
  }

  composer.render();
  requestAnimationFrame(animate);
}
animate();
