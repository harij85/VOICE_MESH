import re
from typing import Any, Dict

COLOR_MAP = {
    # Longer color names first to match before shorter ones
    "electric blue": "#1e3cff",
    "red": "#ff2b2b",
    "blue": "#2b6cff",
    "green": "#2bff6c",
    "purple": "#8b5bff",
    "pink": "#ff4bd8",
    "orange": "#ff8b2b",
    "white": "#ffffff",
    "black": "#101014",
}

STYLE_KEYWORDS = [
    ("futuristic", "futuristic_holo"),
    ("wireframe", "wireframe"),
    ("hologram", "futuristic_holo"),
    ("clay", "clay"),
    ("glossy", "glossy_studio"),
    ("matte", "matte_studio"),
]

CATEGORY_HINTS = [
    (re.compile(r"\b(phone|handset|smartphone)\b"), ("consumer_electronics", "rounded_slab", ["camera_bump"])),
    (re.compile(r"\b(bottle|flask)\b"), ("product_container", "cylinder", [])),
    (re.compile(r"\b(headset|headphones)\b"), ("audio_device", "capsule", [])),
    (re.compile(r"\b(remote|controller)\b"), ("controller", "rounded_box", [])),
]

def parse_command(text: str) -> Dict[str, Any]:
    # Normalize whitespace first
    t = re.sub(r"\s+", " ", text.strip().lower())

    # Check style keywords first (before object commands)
    # to handle cases like "show wireframe"
    for kw, style in STYLE_KEYWORDS:
        if kw in t:
            return {"presentation": {"style": style}}

    # Show object
    m = re.search(r"(show me|show|display|i want to see)\s+(an?\s+)?(.+)$", t)
    if m:
        name = m.group(3).strip().strip("'\"")
        patch: Dict[str, Any] = {
            "object": {"name": name, "category": "generic"},
            "presentation": {"mode": "hero_on_pedestal"},
            "camera": {"orbit": True},
        }
        for rx, (cat, prim, feats) in CATEGORY_HINTS:
            if rx.search(name):
                patch["object"]["category"] = cat
                patch["shape_hint"] = {"primitive": prim, "features": feats}
                break
        return patch

    # Set color (use word boundaries to avoid matching substrings like "red" in "reduce")
    for k, v in COLOR_MAP.items():
        if re.search(rf"\b{re.escape(k)}\b", t):
            return {"material": {"color": v}}

    hexm = re.search(r"#([0-9a-f]{6})\b", t)
    if hexm:
        return {"material": {"color": f"#{hexm.group(1)}"}}

    # Zoom
    if "zoom in" in t or "closer" in t:
        return {"camera": {"distance": 1.6}}
    if "zoom out" in t or "further" in t:
        return {"camera": {"distance": 3.2}}

    # Orbit toggle (check "stop" first to avoid matching "rotating" in "stop rotating")
    if "stop rotating" in t or "stop orbit" in t:
        return {"camera": {"orbit": False}}
    if "start rotating" in t or "rotate" in t or "orbit" in t:
        return {"camera": {"orbit": True}}

    # FX knobs
    if "more outline" in t:
        return {"fx": {"outline": 0.25}}
    if "less outline" in t:
        return {"fx": {"outline": 0.05}}
    if "more bloom" in t or "glow" in t:
        return {"fx": {"bloom": 0.35}}
    if "less bloom" in t or "reduce bloom" in t:
        return {"fx": {"bloom": 0.05}}
    if "fade out" in t or "hide it" in t:
        return {"fx": {"alpha": 0.0}}
    if "fade in" in t or "show it" in t:
        return {"fx": {"alpha": 1.0}}

    # Unknown: no-op (safe)
    return {}