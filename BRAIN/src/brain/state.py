from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any, Dict

DEFAULT_SCENE: Dict[str, Any] = {
    "object": {"name": "demo object", "category": "generic"},
    "presentation": {"mode": "hero_on_pedestal", "style": "glossy_studio"},
    "shape_hint": {
        "primitive": "rounded_box",
        "features": [],
        "dimensions": {
            "width": 0.5,
            "height": 1.0,
            "depth": 0.2,
            "radius": 0.05,
            "segments": 8
        }
    },
    "material": {"preset": "plastic_gloss", "color": "#4b7bff", "roughness": 0.35},
    "camera": {"orbit": True, "distance": 2.2, "fov": 35},
    "lighting": {"preset": "studio_softbox"},
    "fx": {"outline": 0.12, "bloom": 0.15, "alpha": 1.0, "rim": 0.0, "env_reflect": 0.0},
    "generating": False,
    "mesh_url": None,
}

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

@dataclass
class SceneState:
    scene: Dict[str, Any]

    @classmethod
    def new(cls) -> "SceneState":
        return cls(scene=deepcopy(DEFAULT_SCENE))

    def apply_patch(self, patch: Dict[str, Any]) -> None:
        # BUG-005 FIX: Deep-copy the incoming patch so that nested mutable
        # objects (lists, dicts) inside the patch are not shared by reference
        # with the scene state.  Without this, a caller that mutates their
        # patch dict after calling apply_patch() would silently corrupt state.
        patch = deepcopy(patch)

        # Shallow-ish merge like the renderer
        for key, val in patch.items():
            if isinstance(val, dict) and isinstance(self.scene.get(key), dict):
                self.scene[key] = {**self.scene[key], **val}
            else:
                self.scene[key] = val

        # Safety clamps
        cam = self.scene.get("camera", {})
        cam["distance"] = clamp(float(cam.get("distance", 2.2)), 0.8, 8.0)
        # BUG-004 FIX: Clamp FOV — previously unclamped, allowing fov=0 (Three.js
        # divide-by-zero) or extreme values like 360 (inverted frustum).
        cam["fov"] = clamp(float(cam.get("fov", 35)), 5.0, 150.0)
        self.scene["camera"] = cam

        fx = self.scene.get("fx", {})
        fx["outline"] = clamp(float(fx.get("outline", 0.12)), 0.0, 1.0)
        fx["bloom"] = clamp(float(fx.get("bloom", 0.15)), 0.0, 1.5)
        fx["alpha"] = clamp(float(fx.get("alpha", 1.0)), 0.0, 1.0)
        fx["rim"] = clamp(float(fx.get("rim", 0.0)), 0.0, 1.0)
        fx["env_reflect"] = clamp(float(fx.get("env_reflect", 0.0)), 0.0, 1.0)
        self.scene["fx"] = fx

        mat = self.scene.get("material", {})
        if "roughness" in mat:
            mat["roughness"] = clamp(float(mat["roughness"]), 0.0, 1.0)
        self.scene["material"] = mat

        # Dimension clamping
        shape_hint = self.scene.get("shape_hint", {})
        dims = shape_hint.get("dimensions", {})
        if dims:
            if "width" in dims:
                dims["width"] = clamp(float(dims["width"]), 0.05, 5.0)
            if "height" in dims:
                dims["height"] = clamp(float(dims["height"]), 0.05, 5.0)
            if "depth" in dims:
                dims["depth"] = clamp(float(dims["depth"]), 0.05, 5.0)
            if "radius" in dims:
                dims["radius"] = clamp(float(dims["radius"]), 0.05, 3.0)
            if "thickness" in dims:
                dims["thickness"] = clamp(float(dims["thickness"]), 0.01, 1.0)
            if "segments" in dims:
                dims["segments"] = int(clamp(float(dims["segments"]), 8, 128))
            shape_hint["dimensions"] = dims
            self.scene["shape_hint"] = shape_hint

    def to_message(self) -> Dict[str, Any]:
        return {"type": "scene", "scene": self.scene}