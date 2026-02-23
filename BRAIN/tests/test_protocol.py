"""
Tests for protocol.py serialisation and the protocol/schema.json contract.

BUG-012: The schema was missing the `patch` message type and did not allow
the `voice_client` role in `hello` messages.
"""
import json
import os
import pytest
from pathlib import Path
from brain.protocol import dumps, loads


SCHEMA_PATH = Path(__file__).parent.parent.parent / "protocol" / "schema.json"


# ---------------------------------------------------------------------------
# Serialisation helpers (brain/protocol.py)
# ---------------------------------------------------------------------------

class TestDumps:
    def test_dumps_returns_string(self):
        result = dumps({"type": "scene"})
        assert isinstance(result, str)

    def test_dumps_round_trips(self):
        msg = {"type": "command", "text": "make it red"}
        assert json.loads(dumps(msg)) == msg

    def test_dumps_unicode_preserved(self):
        msg = {"text": "héllo wörld"}
        serialised = dumps(msg)
        assert "héllo wörld" in serialised
        # ensure_ascii=False must be honoured
        assert "\\u" not in serialised

    def test_dumps_nested_structure(self):
        msg = {"type": "scene", "scene": {"object": {"name": "demo"}}}
        result = dumps(msg)
        parsed = json.loads(result)
        assert parsed["scene"]["object"]["name"] == "demo"


class TestLoads:
    def test_loads_returns_dict(self):
        result = loads('{"type": "hello"}')
        assert isinstance(result, dict)

    def test_loads_parses_correctly(self):
        raw = '{"type": "command", "text": "zoom in"}'
        result = loads(raw)
        assert result["type"] == "command"
        assert result["text"] == "zoom in"

    def test_loads_round_trips_with_dumps(self):
        original = {"type": "patch", "patch": {"material": {"color": "#ff0000"}}}
        assert loads(dumps(original)) == original

    def test_loads_raises_on_invalid_json(self):
        with pytest.raises(json.JSONDecodeError):
            loads("not valid json")

    def test_loads_handles_unicode(self):
        result = loads('{"text": "héllo"}')
        assert result["text"] == "héllo"


# ---------------------------------------------------------------------------
# Schema structure tests (protocol/schema.json)
# ---------------------------------------------------------------------------

class TestSchemaFile:
    @pytest.fixture
    def schema(self):
        assert SCHEMA_PATH.exists(), f"Schema not found: {SCHEMA_PATH}"
        return json.loads(SCHEMA_PATH.read_text())

    def test_schema_file_is_valid_json(self, schema):
        assert isinstance(schema, dict)

    def test_schema_has_one_of(self, schema):
        assert "oneOf" in schema

    def test_schema_defines_hello(self, schema):
        defs = schema.get("$defs", {})
        assert "hello" in defs

    def test_schema_defines_scene(self, schema):
        defs = schema.get("$defs", {})
        assert "scene" in defs

    def test_schema_defines_command(self, schema):
        defs = schema.get("$defs", {})
        assert "command" in defs

    def test_schema_defines_ping(self, schema):
        defs = schema.get("$defs", {})
        assert "ping" in defs

    # BUG-012: `patch` type was missing from schema
    def test_schema_defines_patch(self, schema):
        defs = schema.get("$defs", {})
        assert "patch" in defs, (
            "BUG-012: `patch` message type is missing from schema.json. "
            "app.py handles patch messages but they were not defined in the schema."
        )

    def test_patch_type_has_required_fields(self, schema):
        patch_def = schema["$defs"]["patch"]
        assert patch_def["required"] == ["type", "patch"]
        assert patch_def["properties"]["type"]["const"] == "patch"

    def test_patch_is_in_one_of(self, schema):
        refs = [entry.get("$ref", "") for entry in schema["oneOf"]]
        assert "#/$defs/patch" in refs, (
            "BUG-012: `patch` must be listed in the top-level `oneOf` array."
        )

    # BUG-012: `voice_client` role missing from hello.role enum
    def test_hello_allows_voice_client_role(self, schema):
        hello_def = schema["$defs"]["hello"]
        role_enum = hello_def["properties"]["role"]["enum"]
        assert "voice_client" in role_enum, (
            "BUG-012: `voice_client` is missing from hello.role enum. "
            "ws_client.py sends role='voice_client' on connect."
        )

    def test_hello_allows_brain_role(self, schema):
        hello_def = schema["$defs"]["hello"]
        role_enum = hello_def["properties"]["role"]["enum"]
        assert "brain" in role_enum

    def test_hello_allows_renderer_role(self, schema):
        hello_def = schema["$defs"]["hello"]
        role_enum = hello_def["properties"]["role"]["enum"]
        assert "renderer" in role_enum

    def test_scene_has_required_fields(self, schema):
        scene_def = schema["$defs"]["scene"]
        inner = scene_def["properties"]["scene"]
        required = inner["required"]
        for field in ["object", "presentation", "material", "camera", "fx"]:
            assert field in required

    def test_fx_has_required_fields(self, schema):
        scene_def = schema["$defs"]["scene"]
        fx = scene_def["properties"]["scene"]["properties"]["fx"]
        for field in ["outline", "bloom", "alpha"]:
            assert field in fx["required"]

    def test_dimensions_has_min_max_constraints(self, schema):
        scene_props = schema["$defs"]["scene"]["properties"]["scene"]["properties"]
        dims = scene_props["shape_hint"]["properties"]["dimensions"]["properties"]
        assert dims["width"]["minimum"] == 0.05
        assert dims["width"]["maximum"] == 5.0
        assert dims["radius"]["minimum"] == 0.05
        assert dims["radius"]["maximum"] == 3.0
        assert dims["segments"]["minimum"] == 8
        assert dims["segments"]["maximum"] == 128
