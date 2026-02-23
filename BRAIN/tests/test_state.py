import pytest
from copy import deepcopy
from brain.state import SceneState, clamp, DEFAULT_SCENE


class TestClampFunction:
    def test_clamp_within_range(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamp_below_range(self):
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamp_above_range(self):
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_clamp_at_lower_bound(self):
        assert clamp(0.0, 0.0, 10.0) == 0.0

    def test_clamp_at_upper_bound(self):
        assert clamp(10.0, 0.0, 10.0) == 10.0


class TestSceneStateCreation:
    def test_new_state_has_defaults(self):
        state = SceneState.new()
        assert state.scene["object"]["name"] == "demo object"
        assert state.scene["object"]["category"] == "generic"
        assert state.scene["camera"]["orbit"] is True
        assert state.scene["camera"]["distance"] == 2.2
        assert state.scene["fx"]["alpha"] == 1.0

    def test_new_state_is_independent(self):
        state1 = SceneState.new()
        state2 = SceneState.new()
        state1.scene["object"]["name"] = "modified"
        assert state2.scene["object"]["name"] == "demo object"


class TestSceneStatePatchMerging:
    def test_simple_patch(self):
        state = SceneState.new()
        state.apply_patch({"material": {"color": "#ff0000"}})
        assert state.scene["material"]["color"] == "#ff0000"
        # Should preserve other material fields
        assert state.scene["material"]["preset"] == "plastic_gloss"

    def test_nested_merge(self):
        state = SceneState.new()
        state.apply_patch({
            "camera": {"distance": 5.0},
            "material": {"color": "#00ff00"}
        })
        assert state.scene["camera"]["distance"] == 5.0
        assert state.scene["camera"]["orbit"] is True  # preserved
        assert state.scene["material"]["color"] == "#00ff00"
        assert state.scene["material"]["preset"] == "plastic_gloss"  # preserved

    def test_top_level_replacement(self):
        state = SceneState.new()
        new_object = {"name": "new thing", "category": "widget"}
        state.apply_patch({"object": new_object})
        assert state.scene["object"]["name"] == "new thing"
        assert state.scene["object"]["category"] == "widget"

    def test_multiple_patches(self):
        state = SceneState.new()
        state.apply_patch({"material": {"color": "#ff0000"}})
        state.apply_patch({"material": {"roughness": 0.8}})
        assert state.scene["material"]["color"] == "#ff0000"
        assert state.scene["material"]["roughness"] == 0.8


class TestSafetyClamping:
    def test_camera_distance_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"distance": 0.5}})
        assert state.scene["camera"]["distance"] == 0.8

    def test_camera_distance_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"distance": 100.0}})
        assert state.scene["camera"]["distance"] == 8.0

    def test_camera_distance_valid_range(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"distance": 3.5}})
        assert state.scene["camera"]["distance"] == 3.5

    def test_fx_outline_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"outline": -0.5}})
        assert state.scene["fx"]["outline"] == 0.0

    def test_fx_outline_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"outline": 2.0}})
        assert state.scene["fx"]["outline"] == 1.0

    def test_fx_bloom_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"bloom": -1.0}})
        assert state.scene["fx"]["bloom"] == 0.0

    def test_fx_bloom_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"bloom": 3.0}})
        assert state.scene["fx"]["bloom"] == 1.5

    def test_fx_alpha_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"alpha": -0.5}})
        assert state.scene["fx"]["alpha"] == 0.0

    def test_fx_alpha_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"alpha": 5.0}})
        assert state.scene["fx"]["alpha"] == 1.0

    def test_material_roughness_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"material": {"roughness": -0.3}})
        assert state.scene["material"]["roughness"] == 0.0

    def test_material_roughness_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"material": {"roughness": 1.5}})
        assert state.scene["material"]["roughness"] == 1.0

    # BUG-004: camera.fov was not clamped — added clamp(5.0, 150.0)
    def test_camera_fov_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"fov": 0}})
        assert state.scene["camera"]["fov"] == 5.0

    def test_camera_fov_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"fov": 360}})
        assert state.scene["camera"]["fov"] == 150.0

    def test_camera_fov_negative(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"fov": -10}})
        assert state.scene["camera"]["fov"] == 5.0

    def test_camera_fov_valid(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"fov": 60}})
        assert state.scene["camera"]["fov"] == 60.0

    def test_camera_fov_preserved_on_unrelated_patch(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"fov": 45}})
        state.apply_patch({"material": {"color": "#ff0000"}})
        assert state.scene["camera"]["fov"] == 45.0

    def test_fx_rim_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"rim": -0.5}})
        assert state.scene["fx"]["rim"] == 0.0

    def test_fx_rim_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"rim": 2.0}})
        assert state.scene["fx"]["rim"] == 1.0

    def test_fx_env_reflect_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"env_reflect": -0.3}})
        assert state.scene["fx"]["env_reflect"] == 0.0

    def test_fx_env_reflect_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"fx": {"env_reflect": 5.0}})
        assert state.scene["fx"]["env_reflect"] == 1.0

    def test_dimension_width_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"shape_hint": {"dimensions": {"width": 0.0}}})
        assert state.scene["shape_hint"]["dimensions"]["width"] == 0.05

    def test_dimension_width_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"shape_hint": {"dimensions": {"width": 10.0}}})
        assert state.scene["shape_hint"]["dimensions"]["width"] == 5.0

    def test_dimension_segments_clamp_low(self):
        state = SceneState.new()
        state.apply_patch({"shape_hint": {"dimensions": {"segments": 4}}})
        assert state.scene["shape_hint"]["dimensions"]["segments"] == 8

    def test_dimension_segments_clamp_high(self):
        state = SceneState.new()
        state.apply_patch({"shape_hint": {"dimensions": {"segments": 256}}})
        assert state.scene["shape_hint"]["dimensions"]["segments"] == 128


class TestPatchReferenceIsolation:
    """BUG-005: Nested objects in the patch were shared by reference.
    Mutating the patch after apply_patch() was silently corrupting state."""

    def test_mutating_patch_dict_after_apply_does_not_corrupt_state(self):
        state = SceneState.new()
        patch = {"material": {"color": "#aabbcc", "roughness": 0.5}}
        state.apply_patch(patch)

        # Mutate the original patch after applying
        patch["material"]["color"] = "#ffffff"

        # State should still hold the value at apply time
        assert state.scene["material"]["color"] == "#aabbcc"

    def test_mutating_patch_list_after_apply_does_not_corrupt_state(self):
        state = SceneState.new()
        features = ["camera_bump", "notch"]
        patch = {"shape_hint": {"primitive": "rounded_slab", "features": features}}
        state.apply_patch(patch)

        # Mutate the list from the original patch
        features.append("extra")

        # State features list should be unchanged
        assert "extra" not in state.scene["shape_hint"]["features"]

    def test_two_states_from_same_patch_are_independent(self):
        patch = {"material": {"color": "#123456"}}
        state1 = SceneState.new()
        state2 = SceneState.new()
        state1.apply_patch(patch)
        state2.apply_patch(patch)

        state1.scene["material"]["color"] = "#ffffff"
        assert state2.scene["material"]["color"] == "#123456"


class TestToMessage:
    def test_to_message_structure(self):
        state = SceneState.new()
        msg = state.to_message()
        assert msg["type"] == "scene"
        assert "scene" in msg
        assert msg["scene"]["object"]["name"] == "demo object"

    def test_to_message_after_patch(self):
        state = SceneState.new()
        state.apply_patch({"material": {"color": "#123456"}})
        msg = state.to_message()
        assert msg["scene"]["material"]["color"] == "#123456"


class TestEdgeCases:
    def test_empty_patch(self):
        state = SceneState.new()
        original = state.scene.copy()
        state.apply_patch({})
        # Scene should be unchanged
        assert state.scene["object"] == original["object"]

    def test_patch_preserves_other_fields(self):
        state = SceneState.new()
        state.apply_patch({"camera": {"distance": 5.0}})
        # All other top-level keys should still exist
        assert "object" in state.scene
        assert "material" in state.scene
        assert "fx" in state.scene
        assert "lighting" in state.scene

    def test_default_scene_not_mutated_by_new(self):
        state1 = SceneState.new()
        state1.apply_patch({"object": {"name": "changed"}})
        state2 = SceneState.new()
        assert state2.scene["object"]["name"] == "demo object"
