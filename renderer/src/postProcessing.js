import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutlinePass } from 'three/examples/jsm/postprocessing/OutlinePass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';

/**
 * Creates an EffectComposer with post-processing pipeline
 * @param {THREE.WebGLRenderer} renderer - The Three.js renderer
 * @param {THREE.Scene} scene - The scene to render
 * @param {THREE.Camera} camera - The camera to use
 * @returns {object} Composer and passes for later updates
 */
export function createComposer(renderer, scene, camera) {
  const composer = new EffectComposer(renderer);

  // Base render pass
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  // Bloom pass (glow effect)
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    0.15, // strength (will be updated from scene spec)
    0.4,  // radius
    0.85  // threshold
  );
  composer.addPass(bloomPass);

  // Outline pass (edge highlighting)
  const outlinePass = new OutlinePass(
    new THREE.Vector2(window.innerWidth, window.innerHeight),
    scene,
    camera
  );
  outlinePass.edgeStrength = 3.0;
  outlinePass.edgeGlow = 0.0;
  outlinePass.edgeThickness = 1.0;
  outlinePass.pulsePeriod = 0; // no pulsing
  outlinePass.visibleEdgeColor.set('#ffffff');
  outlinePass.hiddenEdgeColor.set('#190a05');
  composer.addPass(outlinePass);

  // FXAA for anti-aliasing
  const fxaaPass = new ShaderPass(FXAAShader);
  fxaaPass.material.uniforms['resolution'].value.x = 1 / (window.innerWidth * renderer.getPixelRatio());
  fxaaPass.material.uniforms['resolution'].value.y = 1 / (window.innerHeight * renderer.getPixelRatio());
  composer.addPass(fxaaPass);

  return {
    composer,
    bloomPass,
    outlinePass,
    fxaaPass
  };
}

/**
 * Updates post-processing effects based on scene spec
 * @param {object} passes - Object containing bloom and outline passes
 * @param {object} sceneSpec - Current scene specification
 * @param {THREE.Mesh} currentMesh - The mesh to apply outline to
 */
export function updateEffects(passes, sceneSpec, currentMesh) {
  const { bloomPass, outlinePass } = passes;

  // Update bloom intensity
  if (bloomPass) {
    bloomPass.strength = sceneSpec.fx.bloom || 0.0;
  }

  // Update outline
  if (outlinePass && currentMesh) {
    const outlineIntensity = sceneSpec.fx.outline || 0.0;

    if (outlineIntensity > 0.01) {
      outlinePass.enabled = true;
      outlinePass.selectedObjects = [currentMesh];
      outlinePass.edgeStrength = outlineIntensity * 10.0; // Scale to visible range
    } else {
      outlinePass.enabled = false;
      outlinePass.selectedObjects = [];
    }
  }
}

/**
 * Updates composer resolution when viewport size changes
 * @param {object} passes - Object containing composer and FXAA pass
 * @param {number} width - New width
 * @param {number} height - New height
 * @param {number} pixelRatio - Device pixel ratio
 */
export function updateComposerSize(passes, width, height, pixelRatio) {
  const { composer, fxaaPass } = passes;

  if (composer) {
    composer.setSize(width, height);
  }

  if (fxaaPass) {
    fxaaPass.material.uniforms['resolution'].value.x = 1 / (width * pixelRatio);
    fxaaPass.material.uniforms['resolution'].value.y = 1 / (height * pixelRatio);
  }
}
