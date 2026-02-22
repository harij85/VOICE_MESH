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
