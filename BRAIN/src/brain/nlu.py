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

# BUG-001 FIX: Exact FX phrases that start with "show" must be guarded before
# the object regex, otherwise "show it" matches as object named "it".
_ALPHA_SHOW_PHRASES = {"show it"}
_ALPHA_HIDE_PHRASES = {"hide it"}

def parse_command(text: str) -> Dict[str, Any]:
    # Normalize whitespace first
    t = re.sub(r"\s+", " ", text.strip().lower())

    # BUG-001 FIX: Guard FX alpha phrases before the object-show regex so that
    # "show it" / "hide it" are not consumed as object commands.
    if "hide it" in t:
        return {"fx": {"alpha": 0.0}}
    if "show it" in t:
        return {"fx": {"alpha": 1.0}}

    # BUG-002 FIX: Object-show commands run FIRST.  If a style keyword is
    # embedded in the same phrase ("show me a wireframe phone"), capture both
    # the object and the style in one patch instead of only returning the style.
    m = re.search(r"(show me|show|display|i want to see)\s+(an?\s+)?(.+)$", t)
    if m:
        name = m.group(3).strip().strip("'\"")
        patch: Dict[str, Any] = {
            "object": {"name": name, "category": "generic"},
            "presentation": {"mode": "hero_on_pedestal"},
            "camera": {"orbit": True},
        }
        # Embed style into the same patch if a style keyword appears
        for kw, style in STYLE_KEYWORDS:
            if kw in t:
                patch["presentation"]["style"] = style
                break
        for rx, (cat, prim, feats) in CATEGORY_HINTS:
            if rx.search(name):
                patch["object"]["category"] = cat
                patch["shape_hint"] = {"primitive": prim, "features": feats}
                break
        return patch

    # Style-only commands (no object trigger in the text)
    for kw, style in STYLE_KEYWORDS:
        if kw in t:
            return {"presentation": {"style": style}}

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

    # Enhance (rim + env_reflect)
    if "remove enhance" in t or t == "plain" or t == "flat":
        return {"fx": {"rim": 0.0, "env_reflect": 0.0}}
    if "enhance" in t or "make it pop" in t or "stand out" in t:
        return {"fx": {"rim": 0.6, "env_reflect": 0.3}}
    if "shiny" in t or "shinier" in t:
        return {"material": {"roughness": 0.1}, "fx": {"rim": 0.4, "env_reflect": 0.3}}
    if "more rim" in t or "more edge" in t:
        return {"fx": {"rim": 0.8}}
    if "less rim" in t:
        return {"fx": {"rim": 0.2}}
    if "more reflection" in t:
        return {"fx": {"env_reflect": 0.6}}
    if "less reflection" in t:
        return {"fx": {"env_reflect": 0.1}}

    # FX knobs
    if "more outline" in t:
        return {"fx": {"outline": 0.25}}
    if "less outline" in t:
        return {"fx": {"outline": 0.05}}
    if "more bloom" in t or "glow" in t:
        return {"fx": {"bloom": 0.35}}
    if "less bloom" in t or "reduce bloom" in t:
        return {"fx": {"bloom": 0.05}}
    if "fade out" in t:
        return {"fx": {"alpha": 0.0}}
    if "fade in" in t:
        return {"fx": {"alpha": 1.0}}

    # Unknown: no-op (safe)
    return {}
