import pytest
from brain.nlu import parse_command


class TestObjectCommands:
    def test_show_phone(self):
        result = parse_command("show me a phone prototype")
        assert result["object"]["name"] == "phone prototype"
        assert result["object"]["category"] == "consumer_electronics"
        assert result["shape_hint"]["primitive"] == "rounded_slab"
        assert "camera_bump" in result["shape_hint"]["features"]

    def test_show_bottle(self):
        result = parse_command("show me a bottle")
        assert result["object"]["name"] == "bottle"
        assert result["object"]["category"] == "product_container"
        assert result["shape_hint"]["primitive"] == "cylinder"

    def test_show_headset(self):
        result = parse_command("show a headset")
        assert result["object"]["name"] == "headset"
        assert result["object"]["category"] == "audio_device"

    def test_show_generic_object(self):
        result = parse_command("show me a widget")
        assert result["object"]["name"] == "widget"
        assert result["object"]["category"] == "generic"

    def test_display_variant(self):
        result = parse_command("display an electric car")
        assert result["object"]["name"] == "electric car"

    def test_show_remote(self):
        result = parse_command("show me a remote")
        assert result["object"]["category"] == "controller"
        assert result["shape_hint"]["primitive"] == "rounded_box"

    def test_show_smartphone(self):
        result = parse_command("show me a smartphone")
        assert result["object"]["category"] == "consumer_electronics"
        assert result["shape_hint"]["primitive"] == "rounded_slab"

    # BUG-002: Compound object+style commands should return BOTH object and style
    def test_show_object_with_embedded_style(self):
        result = parse_command("show me a wireframe phone")
        # Should return the object, not just the style
        assert "object" in result
        assert result["object"]["category"] == "consumer_electronics"
        # Should also capture the style
        assert result["presentation"]["style"] == "wireframe"

    def test_show_object_with_futuristic_style(self):
        result = parse_command("show me a futuristic bottle")
        assert "object" in result
        assert result["object"]["category"] == "product_container"
        assert result["presentation"]["style"] == "futuristic_holo"

    def test_show_sets_orbit(self):
        result = parse_command("show me a phone")
        assert result["camera"]["orbit"] is True

    def test_i_want_to_see_variant(self):
        result = parse_command("i want to see a bottle")
        assert result["object"]["name"] == "bottle"
        assert result["object"]["category"] == "product_container"


class TestColorCommands:
    def test_red(self):
        result = parse_command("make it red")
        assert result["material"]["color"] == "#ff2b2b"

    def test_blue(self):
        result = parse_command("make it blue")
        assert result["material"]["color"] == "#2b6cff"

    def test_electric_blue(self):
        result = parse_command("set color to electric blue")
        assert result["material"]["color"] == "#1e3cff"

    def test_hex_color(self):
        result = parse_command("set color to #ff6b2b")
        assert result["material"]["color"] == "#ff6b2b"

    def test_hex_color_uppercase(self):
        result = parse_command("color #FF6B2B")
        assert result["material"]["color"] == "#ff6b2b"

    def test_green(self):
        result = parse_command("make it green")
        assert result["material"]["color"] == "#2bff6c"

    def test_purple(self):
        result = parse_command("make it purple")
        assert result["material"]["color"] == "#8b5bff"

    def test_color_not_match_substrings(self):
        # "red" should not match inside "reduce"
        result = parse_command("reduce bloom")
        assert "material" not in result


class TestCameraCommands:
    def test_zoom_in(self):
        result = parse_command("zoom in")
        assert result["camera"]["distance"] == 1.6

    def test_zoom_out(self):
        result = parse_command("zoom out")
        assert result["camera"]["distance"] == 3.2

    def test_closer(self):
        result = parse_command("get closer")
        assert result["camera"]["distance"] == 1.6

    def test_further(self):
        result = parse_command("move further away")
        assert result["camera"]["distance"] == 3.2

    def test_start_orbit(self):
        result = parse_command("start rotating")
        assert result["camera"]["orbit"] is True

    def test_stop_orbit(self):
        result = parse_command("stop rotating")
        assert result["camera"]["orbit"] is False

    def test_orbit_command(self):
        result = parse_command("orbit the camera")
        assert result["camera"]["orbit"] is True

    def test_stop_orbit_checked_before_rotate(self):
        # "stop rotating" must not be parsed as "rotate" → orbit: True
        result = parse_command("stop rotating please")
        assert result["camera"]["orbit"] is False


class TestStyleCommands:
    def test_futuristic(self):
        result = parse_command("make it more futuristic")
        assert result["presentation"]["style"] == "futuristic_holo"

    def test_wireframe(self):
        result = parse_command("show wireframe")
        assert result["presentation"]["style"] == "wireframe"

    def test_hologram(self):
        result = parse_command("hologram style")
        assert result["presentation"]["style"] == "futuristic_holo"

    def test_glossy(self):
        result = parse_command("make it glossy")
        assert result["presentation"]["style"] == "glossy_studio"

    def test_clay(self):
        result = parse_command("clay render please")
        assert result["presentation"]["style"] == "clay"

    def test_matte(self):
        result = parse_command("make it matte")
        assert result["presentation"]["style"] == "matte_studio"

    def test_style_only_returns_presentation_key(self):
        result = parse_command("futuristic")
        assert list(result.keys()) == ["presentation"]


class TestFXCommands:
    def test_more_outline(self):
        result = parse_command("more outline")
        assert result["fx"]["outline"] == 0.25

    def test_less_outline(self):
        result = parse_command("less outline")
        assert result["fx"]["outline"] == 0.05

    def test_more_bloom(self):
        result = parse_command("add more bloom")
        assert result["fx"]["bloom"] == 0.35

    def test_glow(self):
        result = parse_command("make it glow")
        assert result["fx"]["bloom"] == 0.35

    def test_less_bloom(self):
        result = parse_command("reduce bloom")
        assert result["fx"]["bloom"] == 0.05

    def test_fade_out(self):
        result = parse_command("fade out")
        assert result["fx"]["alpha"] == 0.0

    def test_fade_in(self):
        result = parse_command("fade in")
        assert result["fx"]["alpha"] == 1.0

    def test_hide(self):
        result = parse_command("hide it")
        assert result["fx"]["alpha"] == 0.0

    # BUG-001: "show it" was previously parsed as object named "it"
    def test_show_it_sets_alpha_to_one(self):
        result = parse_command("show it")
        assert "fx" in result, "'show it' should return an FX patch, not an object patch"
        assert result["fx"]["alpha"] == 1.0

    def test_show_it_does_not_create_object(self):
        result = parse_command("show it")
        assert "object" not in result, "'show it' must not create an object named 'it'"

    def test_hide_it_does_not_create_object(self):
        result = parse_command("hide it")
        assert "object" not in result


class TestEnhanceCommands:
    def test_enhance(self):
        result = parse_command("enhance")
        assert result["fx"]["rim"] == 0.6
        assert result["fx"]["env_reflect"] == 0.3

    def test_make_it_pop(self):
        result = parse_command("make it pop")
        assert result["fx"]["rim"] == 0.6
        assert result["fx"]["env_reflect"] == 0.3

    def test_stand_out(self):
        result = parse_command("make it stand out")
        assert result["fx"]["rim"] == 0.6

    def test_more_rim(self):
        result = parse_command("more rim")
        assert result["fx"]["rim"] == 0.8

    def test_more_edge(self):
        result = parse_command("more edge glow")
        assert result["fx"]["rim"] == 0.8

    def test_less_rim(self):
        result = parse_command("less rim")
        assert result["fx"]["rim"] == 0.2

    def test_more_reflection(self):
        result = parse_command("more reflection")
        assert result["fx"]["env_reflect"] == 0.6

    def test_less_reflection(self):
        result = parse_command("less reflection")
        assert result["fx"]["env_reflect"] == 0.1

    def test_remove_enhance(self):
        result = parse_command("remove enhance")
        assert result["fx"]["rim"] == 0.0
        assert result["fx"]["env_reflect"] == 0.0

    def test_plain(self):
        result = parse_command("plain")
        assert result["fx"]["rim"] == 0.0
        assert result["fx"]["env_reflect"] == 0.0

    def test_flat(self):
        result = parse_command("flat")
        assert result["fx"]["rim"] == 0.0
        assert result["fx"]["env_reflect"] == 0.0

    def test_shiny(self):
        result = parse_command("make surface shiny")
        assert result["material"]["roughness"] == 0.1
        assert result["fx"]["rim"] == 0.4
        assert result["fx"]["env_reflect"] == 0.3

    def test_shinier(self):
        result = parse_command("make it shinier")
        assert result["material"]["roughness"] == 0.1
        assert result["fx"]["env_reflect"] == 0.3

    def test_enhance_does_not_create_object(self):
        result = parse_command("enhance")
        assert "object" not in result


class TestEdgeCases:
    def test_unknown_command(self):
        result = parse_command("do a backflip")
        assert result == {}

    def test_empty_command(self):
        result = parse_command("")
        assert result == {}

    def test_whitespace_only(self):
        result = parse_command("   ")
        assert result == {}

    def test_case_insensitive(self):
        result = parse_command("MAKE IT RED")
        assert result["material"]["color"] == "#ff2b2b"

    def test_multiple_spaces(self):
        result = parse_command("show  me   a   phone")
        assert result["object"]["name"] == "phone"

    def test_single_word_unknown(self):
        result = parse_command("xyzzy")
        assert result == {}

    def test_result_is_always_dict(self):
        for cmd in ["", "foo", "show me a phone", "make it red", "zoom in"]:
            result = parse_command(cmd)
            assert isinstance(result, dict)
