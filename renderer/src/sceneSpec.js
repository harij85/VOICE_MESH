export const DEFAULT_SCENE = {
  object: { name: "demo object", category: "generic" },
  presentation: { mode: "hero_on_pedestal", style: "glossy_studio" },
  shape_hint: { primitive: "rounded_box", features: [] },
  material: { preset: "plastic_gloss", color: "#4b7bff", roughness: 0.35 },
  camera: { orbit: true, distance: 2.2, fov: 35 },
  lighting: { preset: "studio_softbox" },
  fx: { outline: 0.12, bloom: 0.15, alpha: 1.0 }
};

export function mergeScene(base, patch) {
  // shallow merge for now; good enough for boilerplate
  return {
    ...base,
    ...patch,
    object: { ...base.object, ...(patch.object ?? {}) },
    presentation: { ...base.presentation, ...(patch.presentation ?? {}) },
    shape_hint: { ...base.shape_hint, ...(patch.shape_hint ?? {}) },
    material: { ...base.material, ...(patch.material ?? {}) },
    camera: { ...base.camera, ...(patch.camera ?? {}) },
    lighting: { ...base.lighting, ...(patch.lighting ?? {}) },
    fx: { ...base.fx, ...(patch.fx ?? {}) }
  };
}