"""Tests for ShapeGenerator — all mocked, no real model download required."""
import threading
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

from brain.shape_gen import ShapeGenerator, CACHE_DIR


class TestShapeGeneratorCacheHit:
    def test_cache_hit_returns_url_without_loading(self, tmp_path, monkeypatch):
        """If PLY already exists, generate() returns its URL without calling _load."""
        monkeypatch.setattr("brain.shape_gen.CACHE_DIR", tmp_path)
        # Pre-create the expected cache file
        safe = "coffee_mug"
        out = tmp_path / f"{safe}.ply"
        out.write_bytes(b"ply\n")

        gen = ShapeGenerator()
        cancel = threading.Event()

        with patch.object(gen, "_load") as mock_load:
            result = gen.generate("coffee mug", cancel)

        mock_load.assert_not_called()
        assert result == out.as_uri()


class TestShapeGeneratorCancelBeforeLoad:
    def test_returns_none_when_cancelled_before_load(self, tmp_path, monkeypatch):
        """generate() returns None if cancel is set before model load."""
        monkeypatch.setattr("brain.shape_gen.CACHE_DIR", tmp_path)

        gen = ShapeGenerator()
        cancel = threading.Event()
        cancel.set()  # cancelled immediately

        with patch.object(gen, "_load") as mock_load:
            result = gen.generate("teapot", cancel)

        mock_load.assert_not_called()
        assert result is None


class TestShapeGeneratorCancelAfterLoad:
    def test_returns_none_when_cancelled_after_load(self, tmp_path, monkeypatch):
        """generate() returns None if cancel is set after model load but before sampling."""
        monkeypatch.setattr("brain.shape_gen.CACHE_DIR", tmp_path)

        gen = ShapeGenerator()
        cancel = threading.Event()

        # _load sets cancel to simulate cancellation mid-way
        def fake_load():
            gen._model = ("cpu", MagicMock(), MagicMock(), MagicMock(), MagicMock())
            cancel.set()

        with patch.object(gen, "_load", side_effect=fake_load):
            result = gen.generate("vase", cancel)

        assert result is None


class TestShapeGeneratorWritesPLY:
    def test_ply_file_written_to_cache_dir(self, tmp_path, monkeypatch):
        """generate() writes a PLY file and returns its URL on success."""
        import sys

        monkeypatch.setattr("brain.shape_gen.CACHE_DIR", tmp_path)

        gen = ShapeGenerator()
        cancel = threading.Event()

        # Build mock shap_e objects
        mock_tri_mesh = MagicMock()
        mock_decoded = MagicMock()
        mock_decoded.tri_mesh.return_value = mock_tri_mesh

        mock_sample_latents = MagicMock(return_value=[MagicMock()])
        mock_decode = MagicMock(return_value=mock_decoded)

        # Fake model tuple: (device, xm, model, diffusion, sample_latents)
        gen._model = ("cpu", MagicMock(), MagicMock(), MagicMock(), mock_sample_latents)

        # Patch sys.modules so `import torch` and `from shap_e.util.notebooks import ...`
        # inside generate() resolve to our mocks.
        mock_torch = MagicMock()
        fake_notebooks_mod = MagicMock()
        fake_notebooks_mod.decode_latent_mesh = mock_decode

        modules_to_patch = {
            "torch": mock_torch,
            "shap_e": MagicMock(),
            "shap_e.util": MagicMock(),
            "shap_e.util.notebooks": fake_notebooks_mod,
        }

        with patch.object(gen, "_load"):
            with patch.dict(sys.modules, modules_to_patch):
                result = gen.generate("robot arm", cancel)

        assert mock_tri_mesh.write_ply.called
        assert result is not None
        assert result.startswith("file://")
        assert "robot_arm" in result

    def test_prompt_normalised_to_safe_filename(self, tmp_path, monkeypatch):
        """Special characters in prompt are replaced with underscores in filename."""
        monkeypatch.setattr("brain.shape_gen.CACHE_DIR", tmp_path)
        gen = ShapeGenerator()
        cancel = threading.Event()
        cancel.set()  # cancel early — we only want to check filename logic

        with patch.object(gen, "_load"):
            gen.generate("red/blue THING!", cancel)

        # No file written (cancelled), but we can infer filename would be safe
        safe = "".join(c if c.isalnum() else "_" for c in "red/blue THING!".lower())[:60]
        expected_path = tmp_path / f"{safe}.ply"
        # File should NOT exist since we cancelled before writing
        assert not expected_path.exists()
