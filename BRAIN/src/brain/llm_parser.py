"""
LLM-based command parser using Claude API.
Converts natural language to structured scene patches with post-validation.
"""
import json
import re
import os
from typing import Any, Dict, Optional
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Canonical patch contract — single source of truth for the LLM prompt,
# post-validation, and runtime state.  Keep in sync with state.py defaults
# and renderer sceneSpec.js / meshGenerator.js.
# ---------------------------------------------------------------------------

ALLOWED_KEYS = {
    "object", "presentation", "shape_hint", "material",
    "camera", "lighting", "fx",
}

ALLOWED_PRIMITIVES = {
    "rounded_box", "rounded_slab", "cylinder", "sphere", "capsule", "torus",
}

ALLOWED_CATEGORIES = {
    "generic", "consumer_electronics", "product_container",
    "audio_device", "controller",
}

ALLOWED_STYLES = {
    "futuristic_holo", "wireframe", "clay", "glossy_studio", "matte_studio",
}

ALLOWED_MODES = {"hero_on_pedestal"}

# Ranges mirror state.py clamp values exactly
FIELD_RANGES: dict[str, tuple[float, float]] = {
    "camera.distance":    (0.8, 8.0),
    "camera.fov":         (5.0, 150.0),
    "material.roughness": (0.0, 1.0),
    "fx.outline":         (0.0, 1.0),
    "fx.bloom":           (0.0, 1.5),
    "fx.alpha":           (0.0, 1.0),
    "fx.rim":             (0.0, 1.0),
    "fx.env_reflect":     (0.0, 1.0),
    "dimensions.width":   (0.05, 5.0),
    "dimensions.height":  (0.05, 5.0),
    "dimensions.depth":   (0.05, 5.0),
    "dimensions.radius":  (0.05, 3.0),
    "dimensions.thickness": (0.01, 1.0),
    "dimensions.segments": (8, 128),
}

NAMED_COLORS = {
    "red": "#ff2b2b", "blue": "#2b6cff", "green": "#2bff6c",
    "purple": "#8b5bff", "pink": "#ff4bd8", "orange": "#ff8b2b",
    "white": "#ffffff", "black": "#101014", "electric blue": "#1e3cff",
    "yellow": "#ffd700", "cyan": "#00ffff", "magenta": "#ff00ff",
    "gold": "#ffd700", "silver": "#c0c0c0", "teal": "#008080",
}

# ---------------------------------------------------------------------------
# System prompt — parser-spec format
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
# Role
You are a deterministic JSON command parser for a 3D scene renderer.
Your ONLY output is a single JSON object (the "patch"). No prose, no markdown fences, no explanation.

# Output contract
Return a JSON object containing ONLY these top-level keys (include only what the command mentions):

  object          — {"name": str, "category": enum}
  presentation    — {"mode": "hero_on_pedestal", "style": enum}
  shape_hint      — {"primitive": enum, "features": [], "dimensions": {partial}}
  material        — {"color": str, "roughness": float}
  camera          — {"orbit": bool, "distance": float, "fov": float}
  lighting        — {"preset": str}
  fx              — {"outline": float, "bloom": float, "alpha": float, "rim": float, "env_reflect": float}

Never invent keys outside this set.

# Enums

primitive:  rounded_box | rounded_slab | cylinder | sphere | capsule | torus
category:   generic | consumer_electronics | product_container | audio_device | controller
style:      futuristic_holo | wireframe | clay | glossy_studio | matte_studio

# Object-to-primitive mapping (use these, not guesses)

phone/smartphone/handset/tablet  → rounded_slab, consumer_electronics
bottle/flask/can/jar             → cylinder, product_container
headset/headphones/earbuds       → capsule, audio_device
remote/controller/gamepad        → rounded_box, controller
ring/donut/bagel                 → torus, generic
ball/globe/marble                → sphere, generic
box/cube/block/crate             → rounded_box, generic

If the object is not listed, pick the closest primitive and use category "generic".

# Value ranges (hard limits — clamp to these)

camera.distance:    0.8 – 8.0    (default 2.2)
camera.fov:         5.0 – 150.0  (default 35)
material.roughness: 0.0 – 1.0    (default 0.35)
fx.outline:         0.0 – 1.0    (default 0.12)
fx.bloom:           0.0 – 1.5    (default 0.15)
fx.alpha:           0.0 – 1.0    (default 1.0)
fx.rim:             0.0 – 1.0    (default 0.0, Fresnel rim light)
fx.env_reflect:     0.0 – 1.0    (default 0.0, environment reflection)
dimensions.width:   0.05 – 5.0
dimensions.height:  0.05 – 5.0
dimensions.depth:   0.05 – 5.0
dimensions.radius:  0.05 – 3.0
dimensions.thickness: 0.01 – 1.0
dimensions.segments: 8 – 128

# Colors

Named: red=#ff2b2b blue=#2b6cff green=#2bff6c purple=#8b5bff pink=#ff4bd8 orange=#ff8b2b white=#ffffff black=#101014 electric blue=#1e3cff yellow=#ffd700 cyan=#00ffff magenta=#ff00ff gold=#ffd700 silver=#c0c0c0 teal=#008080
Always emit hex codes (e.g. "#ff2b2b"), never color names.

# Intent precedence (highest first)

1. Visibility toggle: "show it" → {"fx":{"alpha":1.0}}, "hide it" → {"fx":{"alpha":0.0}}
2. Object creation: "show me a …" → object + shape_hint + camera.orbit:true
3. Style change: "make it futuristic" → presentation.style only
4. Material edit: "make it red", "smoother" → material fields only
5. Camera control: "zoom in", "stop rotating" → camera fields only
6. FX adjustment: "more bloom", "add rim light" → fx fields only
7. Dimension edit: "make it taller" → shape_hint.dimensions only
8. Compound: commands may combine intents ("show me a big red shiny bottle")
   — include ALL relevant fields in one patch

# Dimension adjectives

tall/taller      → height 1.5-2.0       short/shorter     → height 0.3-0.6
wide/wider       → width 1.2-1.8        narrow/thinner    → width 0.2-0.4
thick/thicker    → depth 0.5-0.8        flat/flatter      → depth 0.05-0.15
small/smaller/tiny → scale all dims down by ~40%
large/big/bigger   → scale all dims up by ~40%

# Abstract / creative commands

"make it pop" / "stand out"          → {"fx":{"rim":0.6,"env_reflect":0.3}}
"make it shiny" / "shinier"          → {"material":{"roughness":0.1},"fx":{"rim":0.4,"env_reflect":0.3}}
"make it glow"                       → {"fx":{"bloom":0.5,"rim":0.4}}
"make it plain" / "flat look"        → {"fx":{"rim":0.0,"env_reflect":0.0,"bloom":0.05}}
"make it dramatic"                   → {"fx":{"bloom":0.4,"outline":0.3,"rim":0.5},"lighting":{"preset":"dramatic"}}
"make it subtle" / "tone it down"    → {"fx":{"bloom":0.05,"outline":0.05,"rim":0.1}}
"make it transparent" / "see through" → {"fx":{"alpha":0.4}}
"make it solid" / "opaque"           → {"fx":{"alpha":1.0}}
"enhance it" / "premium look"        → {"fx":{"rim":0.6,"env_reflect":0.3},"material":{"roughness":0.15}}
"make it matte" / "less shiny"       → {"material":{"roughness":0.8},"fx":{"env_reflect":0.0}}
"make it rough" / "textured"         → {"material":{"roughness":0.9}}
"reset effects"                      → {"fx":{"outline":0.12,"bloom":0.15,"alpha":1.0,"rim":0.0,"env_reflect":0.0}}

# Ambiguity policy

- If intent is unclear, prefer a conservative interpretation over a wild guess.
- If the command is truly unintelligible or unrelated to 3D scene control, return {}.
- Never hallucinate fields. Only include what was asked for.
- ASR noise: tolerate minor misspellings ("blume" → bloom, "shere" → sphere).

# Examples

"show me a phone"
{"object":{"name":"phone","category":"consumer_electronics"},"shape_hint":{"primitive":"rounded_slab","features":["camera_bump"],"dimensions":{"width":0.35,"height":0.75,"depth":0.08}},"camera":{"orbit":true}}

"show me a big shiny red bottle"
{"object":{"name":"bottle","category":"product_container"},"shape_hint":{"primitive":"cylinder","dimensions":{"radius":0.45,"height":1.8}},"material":{"color":"#ff2b2b","roughness":0.1},"fx":{"rim":0.4,"env_reflect":0.3},"camera":{"orbit":true}}

"make it blue and add more bloom"
{"material":{"color":"#2b6cff"},"fx":{"bloom":0.4}}

"make it taller and less shiny"
{"shape_hint":{"dimensions":{"height":1.8}},"material":{"roughness":0.7}}

"zoom in closer"
{"camera":{"distance":1.4}}

"stop rotating"
{"camera":{"orbit":false}}

"give it a wireframe look"
{"presentation":{"style":"wireframe"}}

"show me a small golden sphere with rim lighting"
{"object":{"name":"sphere","category":"generic"},"shape_hint":{"primitive":"sphere","dimensions":{"radius":0.3}},"material":{"color":"#ffd700"},"fx":{"rim":0.6},"camera":{"orbit":true}}

"fade out slowly"
{"fx":{"alpha":0.0}}

"make it really pop and glow"
{"fx":{"rim":0.7,"env_reflect":0.3,"bloom":0.5}}

"I don't know, something cool"
{"presentation":{"style":"futuristic_holo"},"fx":{"rim":0.5,"bloom":0.3}}

"reduce everything"
{"fx":{"outline":0.05,"bloom":0.05,"rim":0.0,"env_reflect":0.0}}

"what's the weather like"
{}
"""


# ---------------------------------------------------------------------------
# Post-validation — strip unknown keys, clamp ranges, fix types
# ---------------------------------------------------------------------------

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def validate_patch(patch: dict) -> dict:
    """Validate and sanitise an LLM-produced patch. Returns cleaned patch."""
    if not isinstance(patch, dict):
        return {}

    # Strip unknown top-level keys
    cleaned: dict[str, Any] = {}
    for key in patch:
        if key in ALLOWED_KEYS:
            cleaned[key] = patch[key]

    # --- object ---
    obj = cleaned.get("object")
    if isinstance(obj, dict):
        obj["name"] = str(obj.get("name", "object"))
        cat = obj.get("category", "generic")
        obj["category"] = cat if cat in ALLOWED_CATEGORIES else "generic"
        cleaned["object"] = obj
    elif "object" in cleaned:
        del cleaned["object"]

    # --- presentation ---
    pres = cleaned.get("presentation")
    if isinstance(pres, dict):
        if "style" in pres and pres["style"] not in ALLOWED_STYLES:
            del pres["style"]
        if "mode" in pres and pres["mode"] not in ALLOWED_MODES:
            pres["mode"] = "hero_on_pedestal"
        if pres:
            cleaned["presentation"] = pres
        else:
            del cleaned["presentation"]
    elif "presentation" in cleaned:
        del cleaned["presentation"]

    # --- shape_hint ---
    sh = cleaned.get("shape_hint")
    if isinstance(sh, dict):
        if "primitive" in sh and sh["primitive"] not in ALLOWED_PRIMITIVES:
            sh["primitive"] = "rounded_box"
        dims = sh.get("dimensions")
        if isinstance(dims, dict):
            for dk in list(dims.keys()):
                rng = FIELD_RANGES.get(f"dimensions.{dk}")
                if rng:
                    try:
                        v = int(dims[dk]) if dk == "segments" else float(dims[dk])
                        dims[dk] = _clamp(v, rng[0], rng[1])
                    except (TypeError, ValueError):
                        del dims[dk]
                else:
                    del dims[dk]  # unknown dimension key
            sh["dimensions"] = dims
        cleaned["shape_hint"] = sh
    elif "shape_hint" in cleaned:
        del cleaned["shape_hint"]

    # --- material ---
    mat = cleaned.get("material")
    if isinstance(mat, dict):
        if "color" in mat:
            c = str(mat["color"])
            if not re.match(r"^#[0-9a-fA-F]{6}$", c):
                # Try named colour lookup
                c_lower = c.lower().strip("#")
                mat["color"] = NAMED_COLORS.get(c_lower, "#4b7bff")
            else:
                mat["color"] = c.lower()
        if "roughness" in mat:
            try:
                mat["roughness"] = _clamp(float(mat["roughness"]), 0.0, 1.0)
            except (TypeError, ValueError):
                del mat["roughness"]
        cleaned["material"] = mat
    elif "material" in cleaned:
        del cleaned["material"]

    # --- camera ---
    cam = cleaned.get("camera")
    if isinstance(cam, dict):
        if "distance" in cam:
            try:
                cam["distance"] = _clamp(float(cam["distance"]), 0.8, 8.0)
            except (TypeError, ValueError):
                del cam["distance"]
        if "fov" in cam:
            try:
                cam["fov"] = _clamp(float(cam["fov"]), 5.0, 150.0)
            except (TypeError, ValueError):
                del cam["fov"]
        if "orbit" in cam:
            cam["orbit"] = bool(cam["orbit"])
        cleaned["camera"] = cam
    elif "camera" in cleaned:
        del cleaned["camera"]

    # --- lighting ---
    lit = cleaned.get("lighting")
    if isinstance(lit, dict):
        if "preset" in lit:
            lit["preset"] = str(lit["preset"])
        cleaned["lighting"] = lit
    elif "lighting" in cleaned:
        del cleaned["lighting"]

    # --- fx ---
    fx = cleaned.get("fx")
    if isinstance(fx, dict):
        allowed_fx = {"outline", "bloom", "alpha", "rim", "env_reflect"}
        for fk in list(fx.keys()):
            if fk not in allowed_fx:
                del fx[fk]
                continue
            rng = FIELD_RANGES.get(f"fx.{fk}")
            if rng:
                try:
                    fx[fk] = _clamp(float(fx[fk]), rng[0], rng[1])
                except (TypeError, ValueError):
                    del fx[fk]
        if fx:
            cleaned["fx"] = fx
        else:
            del cleaned["fx"]
    elif "fx" in cleaned:
        del cleaned["fx"]

    return cleaned


# ---------------------------------------------------------------------------
# Parser class
# ---------------------------------------------------------------------------

class LLMCommandParser:
    """Parses natural language commands using Claude with post-validation."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key."
            )
        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        print(f"[llm] Initialized with model: {model}")

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse natural language command into a validated scene patch."""
        print(f"[llm] Parsing: '{text}'")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": text}],
            )

            content = response.content[0].text.strip()
            print(f"[llm] Raw: {content}")

            # Strip markdown fences if present
            if content.startswith("```"):
                content = re.sub(r"^```(?:json)?\s*", "", content)
                content = re.sub(r"\s*```$", "", content)
                content = content.strip()

            patch = json.loads(content)

            # Post-validate and sanitise
            patch = validate_patch(patch)
            print(f"[llm] Validated patch: {json.dumps(patch)}")

            return patch

        except json.JSONDecodeError as e:
            print(f"[llm] JSON parse error: {e}")
            print(f"[llm] Raw response: {content}")  # noqa: F821
            return {}
        except Exception as e:
            print(f"[llm] Error: {e}")
            return {}


# ---------------------------------------------------------------------------
# Manual test harness
# ---------------------------------------------------------------------------

def test_llm_parser():
    """Test function: Parse various natural language commands."""
    print("\n=== LLM Command Parser Test ===\n")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set.")
        print("  1. Get key from https://console.anthropic.com/")
        print("  2. Create BRAIN/.env with: ANTHROPIC_API_KEY=your_key_here")
        return

    try:
        parser = LLMCommandParser()
    except Exception as e:
        print(f"Failed to init: {e}")
        return

    # Broad test set covering all intent classes + hard cases
    test_commands = [
        # Object creation
        "show me a phone prototype",
        "show me a big shiny red bottle",
        "show me a small golden sphere with rim lighting",
        # Material edits
        "make it red",
        "make it smoother",
        # Camera
        "zoom in closer",
        "stop rotating",
        # FX
        "add more bloom and glow",
        "make it pop",
        "tone it down",
        # Style
        "make it more futuristic",
        "give it a wireframe look",
        # Dimension
        "make it taller and wider",
        # Compound
        "make it blue, shiny, and add rim light",
        # Abstract / creative
        "make it look premium",
        "something dramatic",
        # Visibility
        "fade out slowly",
        "show it",
        # Noisy ASR
        "sho me a blew shere",
        # Unintelligible
        "what's the weather like",
    ]

    print(f"Testing {len(test_commands)} commands:\n")
    passed = 0
    failed = 0

    for cmd in test_commands:
        print(f"  > '{cmd}'")
        patch = parser.parse(cmd)
        if isinstance(patch, dict):
            print(f"    {json.dumps(patch)}")
            passed += 1
        else:
            print(f"    FAIL: not a dict")
            failed += 1
        print()

    print(f"{'='*60}")
    print(f"Results: {passed}/{len(test_commands)} returned valid patches")
    if failed:
        print(f"  {failed} commands returned invalid output")


if __name__ == "__main__":
    test_llm_parser()
