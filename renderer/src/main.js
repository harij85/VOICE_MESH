import * as THREE from "three";
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { createWsClient } from "./wsClient.js";
import { DEFAULT_SCENE, mergeScene } from "./sceneSpec.js";
import { createGeometry } from "./meshGenerator.js";
import { createComposer, updateEffects, updateComposerSize } from "./postProcessing.js";

const hud = document.getElementById("hud");
const viewport = document.getElementById("viewport");
const resizeHandle = document.getElementById("resize-handle");

let sceneSpec = structuredClone(DEFAULT_SCENE);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
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

// Position camera based on scene spec
function updateCameraPosition() {
  const distance = sceneSpec.camera.distance;
  const angle = cameraAngle;
  const elevation = cameraElevation;

  camera.position.x = distance * Math.cos(elevation) * Math.sin(angle);
  camera.position.y = distance * Math.sin(elevation);
  camera.position.z = distance * Math.cos(elevation) * Math.cos(angle);
  camera.lookAt(0, 0, 0);
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

/**
 * Updates the 3D mesh based on scene spec
 * CRITICAL: Disposes old geometry/material to prevent memory leaks
 */
function updateMesh() {
  // Dispose old mesh
  if (currentMesh) {
    scene.remove(currentMesh);
    if (currentMesh.geometry) currentMesh.geometry.dispose();
    if (currentMesh.material) currentMesh.material.dispose();
  }

  // Create new geometry from scene spec
  const primitive = sceneSpec.shape_hint?.primitive || 'rounded_box';
  const dimensions = sceneSpec.shape_hint?.dimensions || {};
  const geometry = createGeometry(primitive, dimensions);

  // Create PBR material
  const material = new THREE.MeshStandardMaterial({
    color: new THREE.Color(sceneSpec.material.color),
    roughness: sceneSpec.material.roughness ?? 0.35,
    metalness: 0.1,
    transparent: true,
    opacity: sceneSpec.fx.alpha ?? 1.0,
    side: THREE.FrontSide
  });

  currentMesh = new THREE.Mesh(geometry, material);
  scene.add(currentMesh);
}

// Initialize with default mesh
updateMesh();

// Initialize post-processing composer
const passes = createComposer(renderer, scene, camera);
const { composer } = passes;

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
}
window.addEventListener("resize", resize);
resize();

const clock = new THREE.Clock();

function applySceneSpec(next) {
  const prevPrimitive = sceneSpec.shape_hint?.primitive;
  const prevDimensions = JSON.stringify(sceneSpec.shape_hint?.dimensions || {});

  sceneSpec = mergeScene(sceneSpec, next);

  const newPrimitive = sceneSpec.shape_hint?.primitive;
  const newDimensions = JSON.stringify(sceneSpec.shape_hint?.dimensions || {});

  // Regenerate mesh if primitive or dimensions changed
  if (prevPrimitive !== newPrimitive || prevDimensions !== newDimensions) {
    updateMesh();
  } else if (currentMesh && currentMesh.material) {
    // Just update material properties if mesh didn't change
    currentMesh.material.color.set(sceneSpec.material.color);
    currentMesh.material.roughness = sceneSpec.material.roughness ?? 0.35;
    currentMesh.material.opacity = sceneSpec.fx.alpha ?? 1.0;
  }

  // Update camera
  updateCameraPosition();
  camera.fov = sceneSpec.camera.fov || 35;
  camera.updateProjectionMatrix();

  // Update post-processing effects
  updateEffects(passes, sceneSpec, currentMesh);

  hud.textContent =
`WS: connected
Object: ${sceneSpec.object.name} (${sceneSpec.object.category})
Primitive: ${sceneSpec.shape_hint?.primitive || 'rounded_box'}
Style: ${sceneSpec.presentation.style}
Material: ${sceneSpec.material.preset} ${sceneSpec.material.color}
Camera: ${sceneSpec.camera.orbit ? "orbit" : "static"} dist=${sceneSpec.camera.distance.toFixed(2)}
FX: outline=${sceneSpec.fx.outline.toFixed(2)} bloom=${sceneSpec.fx.bloom.toFixed(2)} alpha=${sceneSpec.fx.alpha.toFixed(2)}`;
}

const ws = createWsClient({
  url: `ws://${location.hostname}:8765`,
  onScene: (s) => applySceneSpec(s),
  onStatus: (t) => (hud.textContent = t)
});

// Handy: type commands with keyboard (demo fallback)
window.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const text = prompt("Command (e.g. show me a phone prototype):");
    if (text) ws.sendCommand(text);
  }
});

// Auto-rotation when orbit is enabled
let autoRotationAngle = 0;

function animate() {
  const delta = clock.getDelta();

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
