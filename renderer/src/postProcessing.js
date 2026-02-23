import * as THREE from 'three';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutlinePass } from 'three/examples/jsm/postprocessing/OutlinePass.js';
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/examples/jsm/shaders/FXAAShader.js';

// ---------------------------------------------------------------------------
// Alpha-preserving bloom compositor
// ---------------------------------------------------------------------------
// UnrealBloomPass's final composite step overwrites the alpha channel because
// it blends additively into the render target using THREE.AdditiveBlending.
// This custom ShaderPass reads the bloom texture and adds its RGB to the
// current buffer WITHOUT touching alpha — preserving the object's transparency
// for clean D3/disguise/NDI compositing.
const AlphaPreservingBloomCompositor = {
  uniforms: {
    tDiffuse: { value: null },   // current buffer (base render)
    tBloom:   { value: null },   // bloom texture
    strength: { value: 1.0 }
  },
  vertexShader: `
    varying vec2 vUv;
    void main() {
      vUv = uv;
      gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    }
  `,
  fragmentShader: `
    uniform sampler2D tDiffuse;
    uniform sampler2D tBloom;
    uniform float strength;
    varying vec2 vUv;
    void main() {
      vec4 base  = texture2D(tDiffuse, vUv);
      vec4 bloom = texture2D(tBloom,   vUv);
      // Add bloom RGB only — preserve base alpha so background stays transparent
      gl_FragColor = vec4(base.rgb + bloom.rgb * strength, base.a);
    }
  `
};

/**
 * Creates an EffectComposer with an alpha-aware post-processing pipeline.
 *
 * Alpha transparency design:
 *   - The EffectComposer is given an RGBA render target so alpha is never
 *     discarded between passes.
 *   - Bloom is composited with a custom shader that adds bloom RGB without
 *     modifying the alpha channel (UnrealBloomPass's built-in compositor
 *     would otherwise set alpha=1 everywhere).
 *   - The final output on the canvas therefore has alpha=0 for background
 *     pixels and alpha=fx.alpha for object pixels — ready for D3/NDI/Syphon.
 *
 * @param {THREE.WebGLRenderer} renderer
 * @param {THREE.Scene} scene
 * @param {THREE.Camera} camera
 * @returns {object} Passes for later updates
 */
export function createComposer(renderer, scene, camera) {
  const w = window.innerWidth;
  const h = window.innerHeight;

  // Alpha-enabled render target — this is the key fix.
  // By default EffectComposer creates targets without alpha, which silently
  // drops transparency on every pass.
  const alphaTarget = new THREE.WebGLRenderTarget(w, h, {
    minFilter: THREE.LinearFilter,
    magFilter: THREE.LinearFilter,
    format: THREE.RGBAFormat,
    type: THREE.UnsignedByteType,
    colorSpace: THREE.SRGBColorSpace,
  });

  const composer = new EffectComposer(renderer, alphaTarget);

  // 1. Base scene render (alpha preserved because target has RGBA format)
  const renderPass = new RenderPass(scene, camera);
  composer.addPass(renderPass);

  // 2. Bloom — rendered to a separate off-screen target, then composited
  //    by AlphaPreservingBloomCompositor below.  We disable the bloom pass's
  //    own built-in compositor step so it doesn't write to the main buffer.
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(w, h),
    0.15,  // strength  (updated in updateEffects)
    0.4,   // radius
    0.85   // threshold
  );
  // renderToScreen=false keeps bloom result in bloomPass.renderTargetsHorizontal[0]
  // so our compositor can sample it as tBloom.
  bloomPass.renderToScreen = false;
  composer.addPass(bloomPass);

  // 3. Alpha-preserving bloom compositor — mixes bloom RGB into base without
  //    touching alpha.
  const bloomCompositor = new ShaderPass(AlphaPreservingBloomCompositor);
  // Wire bloomPass output texture into the compositor's tBloom sampler.
  // UnrealBloomPass exposes the final blurred result on renderTargetsHorizontal[0].
  bloomCompositor.uniforms.tBloom.value =
    bloomPass.renderTargetsHorizontal[0].texture;
  composer.addPass(bloomCompositor);

  // 4. Outline pass (edge highlighting)
  const outlinePass = new OutlinePass(new THREE.Vector2(w, h), scene, camera);
  outlinePass.edgeStrength = 3.0;
  outlinePass.edgeGlow = 0.0;
  outlinePass.edgeThickness = 1.0;
  outlinePass.pulsePeriod = 0;
  outlinePass.visibleEdgeColor.set('#ffffff');
  outlinePass.hiddenEdgeColor.set('#190a05');
  composer.addPass(outlinePass);

  // 5. FXAA anti-aliasing
  const fxaaPass = new ShaderPass(FXAAShader);
  fxaaPass.material.uniforms['resolution'].value.x =
    1 / (w * renderer.getPixelRatio());
  fxaaPass.material.uniforms['resolution'].value.y =
    1 / (h * renderer.getPixelRatio());
  composer.addPass(fxaaPass);

  return { composer, bloomPass, bloomCompositor, outlinePass, fxaaPass, alphaTarget };
}

/**
 * Updates post-processing effects from the current scene spec.
 * @param {object} passes
 * @param {object} sceneSpec
 * @param {THREE.Mesh} currentMesh
 */
export function updateEffects(passes, sceneSpec, currentMesh) {
  const { bloomPass, bloomCompositor, outlinePass } = passes;

  if (bloomPass) {
    const strength = sceneSpec.fx.bloom || 0.0;
    bloomPass.strength = strength;
    // Also sync the compositor uniform so the alpha-preserving blend uses
    // the same strength value as the original bloom pass.
    if (bloomCompositor) {
      bloomCompositor.uniforms.strength.value = strength;
    }
  }

  if (outlinePass && currentMesh) {
    const intensity = sceneSpec.fx.outline || 0.0;
    if (intensity > 0.01) {
      outlinePass.enabled = true;
      outlinePass.selectedObjects = [currentMesh];
      outlinePass.edgeStrength = intensity * 10.0;
    } else {
      outlinePass.enabled = false;
      outlinePass.selectedObjects = [];
    }
  }
}

/**
 * Updates composer and FXAA resolution when the viewport is resized.
 * @param {object} passes
 * @param {number} width
 * @param {number} height
 * @param {number} pixelRatio
 */
export function updateComposerSize(passes, width, height, pixelRatio) {
  const { composer, fxaaPass, alphaTarget } = passes;

  if (composer) {
    composer.setSize(width, height);
  }

  // Keep the alpha render target in sync with the new viewport size.
  if (alphaTarget) {
    alphaTarget.setSize(width, height);
  }

  if (fxaaPass) {
    fxaaPass.material.uniforms['resolution'].value.x = 1 / (width * pixelRatio);
    fxaaPass.material.uniforms['resolution'].value.y = 1 / (height * pixelRatio);
  }
}
