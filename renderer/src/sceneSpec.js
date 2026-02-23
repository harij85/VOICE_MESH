// BUG-007 FIX: JS DEFAULT_SCENE was missing the `dimensions` key under
// shape_hint, which diverged from Python's DEFAULT_SCENE.  When the renderer
// starts before BRAIN sends its initial scene, dimension-based code in
// meshGenerator.js would encounter `undefined` instead of sensible defaults.
export const DEFAULT_SCENE = {
  object: { name: "demo object", category: "generic" },
  presentation: { mode: "hero_on_pedestal", style: "glossy_studio" },
  shape_hint: {
    primitive: "rounded_box",
    features: [],
    dimensions: { width: 0.5, height: 1.0, depth: 0.2, radius: 0.05, segments: 8 }
  },
  material: { preset: "plastic_gloss", color: "#4b7bff", roughness: 0.35 },
  camera: { orbit: true, distance: 2.2, fov: 35 },
  lighting: { preset: "studio_softbox" },
  fx: { outline: 0.12, bloom: 0.15, alpha: 1.0, rim: 0.0, env_reflect: 0.0 },
  generating: false,
  mesh_url: null
};

export function mergeScene(base, patch) {
  // BUG-006 FIX: shape_hint.dimensions was shallow-merged, meaning a patch
  // with only `{ shape_hint: { dimensions: { width: 1.5 } } }` would replace
  // the entire dimensions object, dropping height, depth, radius, segments.
  // Now dimensions are deep-merged independently from the rest of shape_hint.
  return {
    ...base,
    ...patch,
    object: { ...base.object, ...(patch.object ?? {}) },
    presentation: { ...base.presentation, ...(patch.presentation ?? {}) },
    shape_hint: {
      ...base.shape_hint,
      ...(patch.shape_hint ?? {}),
      dimensions: {
        ...(base.shape_hint?.dimensions ?? {}),
        ...(patch.shape_hint?.dimensions ?? {})
      }
    },
    material: { ...base.material, ...(patch.material ?? {}) },
    camera: { ...base.camera, ...(patch.camera ?? {}) },
    lighting: { ...base.lighting, ...(patch.lighting ?? {}) },
    fx: { ...base.fx, ...(patch.fx ?? {}) }
  };
}
