"""Tests for LLM parser post-validation (no API key required)."""
import pytest
from brain.llm_parser import validate_patch


class TestValidatePatchStripUnknownKeys:
    def test_strips_unknown_top_level_keys(self):
        patch = {"object": {"name": "x", "category": "generic"}, "garbage": True, "foo": 1}
        result = validate_patch(patch)
        assert "garbage" not in result
        assert "foo" not in result
        assert "object" in result

    def test_empty_patch(self):
        assert validate_patch({}) == {}

    def test_non_dict_returns_empty(self):
        assert validate_patch("hello") == {}
        assert validate_patch(None) == {}
        assert validate_patch([1, 2]) == {}


class TestValidateObject:
    def test_valid_object(self):
        p = validate_patch({"object": {"name": "phone", "category": "consumer_electronics"}})
        assert p["object"]["name"] == "phone"
        assert p["object"]["category"] == "consumer_electronics"

    def test_unknown_category_defaults_generic(self):
        p = validate_patch({"object": {"name": "thing", "category": "INVALID"}})
        assert p["object"]["category"] == "generic"

    def test_non_dict_object_stripped(self):
        p = validate_patch({"object": "not a dict"})
        assert "object" not in p


class TestValidatePresentation:
    def test_valid_style(self):
        p = validate_patch({"presentation": {"style": "wireframe"}})
        assert p["presentation"]["style"] == "wireframe"

    def test_invalid_style_stripped(self):
        p = validate_patch({"presentation": {"style": "neon_glow"}})
        assert "presentation" not in p  # empty after stripping invalid style

    def test_invalid_mode_defaults(self):
        p = validate_patch({"presentation": {"mode": "BAD", "style": "clay"}})
        assert p["presentation"]["mode"] == "hero_on_pedestal"


class TestValidateShapeHint:
    def test_valid_primitive(self):
        p = validate_patch({"shape_hint": {"primitive": "cylinder"}})
        assert p["shape_hint"]["primitive"] == "cylinder"

    def test_invalid_primitive_defaults(self):
        p = validate_patch({"shape_hint": {"primitive": "pyramid"}})
        assert p["shape_hint"]["primitive"] == "rounded_box"

    def test_dimensions_clamped(self):
        p = validate_patch({"shape_hint": {"dimensions": {"width": 100.0, "height": -5.0}}})
        assert p["shape_hint"]["dimensions"]["width"] == 5.0
        assert p["shape_hint"]["dimensions"]["height"] == 0.05

    def test_unknown_dimension_key_stripped(self):
        p = validate_patch({"shape_hint": {"dimensions": {"width": 1.0, "bogus": 99}}})
        assert "bogus" not in p["shape_hint"]["dimensions"]
        assert p["shape_hint"]["dimensions"]["width"] == 1.0

    def test_segments_clamped_to_int(self):
        p = validate_patch({"shape_hint": {"dimensions": {"segments": 5}}})
        assert p["shape_hint"]["dimensions"]["segments"] == 8  # min 8

    def test_non_dict_shape_hint_stripped(self):
        p = validate_patch({"shape_hint": "sphere"})
        assert "shape_hint" not in p


class TestValidateMaterial:
    def test_valid_hex_color(self):
        p = validate_patch({"material": {"color": "#ff0000"}})
        assert p["material"]["color"] == "#ff0000"

    def test_named_color_resolved(self):
        p = validate_patch({"material": {"color": "red"}})
        assert p["material"]["color"] == "#ff2b2b"

    def test_invalid_color_defaults(self):
        p = validate_patch({"material": {"color": "rainbow"}})
        assert p["material"]["color"] == "#4b7bff"  # default

    def test_roughness_clamped(self):
        p = validate_patch({"material": {"roughness": 5.0}})
        assert p["material"]["roughness"] == 1.0

    def test_roughness_invalid_type_stripped(self):
        p = validate_patch({"material": {"roughness": "very"}})
        assert "roughness" not in p["material"]


class TestValidateCamera:
    def test_distance_clamped(self):
        p = validate_patch({"camera": {"distance": 0.1}})
        assert p["camera"]["distance"] == 0.8

    def test_orbit_coerced_to_bool(self):
        p = validate_patch({"camera": {"orbit": 1}})
        assert p["camera"]["orbit"] is True

    def test_fov_clamped(self):
        p = validate_patch({"camera": {"fov": 0}})
        assert p["camera"]["fov"] == 5.0


class TestValidateFx:
    def test_valid_fx(self):
        p = validate_patch({"fx": {"bloom": 0.5, "rim": 0.3, "env_reflect": 0.2}})
        assert p["fx"]["bloom"] == 0.5
        assert p["fx"]["rim"] == 0.3
        assert p["fx"]["env_reflect"] == 0.2

    def test_unknown_fx_key_stripped(self):
        p = validate_patch({"fx": {"bloom": 0.5, "sparkle": 1.0}})
        assert "sparkle" not in p["fx"]

    def test_fx_values_clamped(self):
        p = validate_patch({"fx": {"bloom": 10.0, "alpha": -1.0}})
        assert p["fx"]["bloom"] == 1.5
        assert p["fx"]["alpha"] == 0.0

    def test_empty_fx_after_strip_removed(self):
        p = validate_patch({"fx": {"sparkle": 1.0}})
        assert "fx" not in p


class TestValidateCompound:
    """Compound patches with multiple sections."""

    def test_full_object_creation_patch(self):
        p = validate_patch({
            "object": {"name": "bottle", "category": "product_container"},
            "shape_hint": {"primitive": "cylinder", "dimensions": {"radius": 0.3, "height": 1.5}},
            "material": {"color": "#ff0000", "roughness": 0.2},
            "fx": {"rim": 0.5, "env_reflect": 0.3},
            "camera": {"orbit": True, "distance": 2.0},
        })
        assert p["object"]["name"] == "bottle"
        assert p["shape_hint"]["primitive"] == "cylinder"
        assert p["material"]["color"] == "#ff0000"
        assert p["fx"]["rim"] == 0.5
        assert p["camera"]["orbit"] is True

    def test_mixed_valid_and_invalid(self):
        p = validate_patch({
            "material": {"color": "#00ff00"},
            "INVALID_KEY": 999,
            "fx": {"bloom": 0.3, "alien_glow": 5.0},
        })
        assert "INVALID_KEY" not in p
        assert p["material"]["color"] == "#00ff00"
        assert "alien_glow" not in p["fx"]
        assert p["fx"]["bloom"] == 0.3
