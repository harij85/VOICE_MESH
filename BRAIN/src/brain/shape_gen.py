"""Shap-E text-to-3D mesh generator (MPS / CPU fallback)."""
import threading
import tempfile
from pathlib import Path

CACHE_DIR = Path(tempfile.gettempdir()) / "voice_mesh_gen"


class ShapeGenerator:
    def __init__(self):
        self._model = None  # lazy-loaded on first call
        self._lock = threading.Lock()

    def _load(self):
        """Load Shap-E models once; shared across calls."""
        if self._model is not None:
            return
        import torch
        from shap_e.diffusion.sample import sample_latents
        from shap_e.diffusion.gaussian_diffusion import diffusion_from_config
        from shap_e.models.download import load_model, load_config

        # MPS deadlocks on shap-e's diffusion forward pass; use CPU instead.
        # Apple Silicon CPU is fast enough (~60-90s for 32 steps).
        device = torch.device("cpu")
        xm = load_model("transmitter", device=device)
        model = load_model("text300M", device=device)
        diffusion = diffusion_from_config(load_config("diffusion"))
        self._model = (device, xm, model, diffusion, sample_latents)

    def generate(self, prompt: str, cancel: threading.Event) -> str | None:
        """
        Runs Shap-E synchronously (call via run_in_executor).
        Returns a file:// URL to the generated PLY, or None if cancelled.
        """
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        safe = "".join(c if c.isalnum() else "_" for c in prompt.lower())[:60]
        out = CACHE_DIR / f"{safe}.ply"

        if out.exists():
            return out.as_uri()  # cache hit — instant

        if cancel.is_set():
            return None

        with self._lock:
            self._load()

        if cancel.is_set():
            return None

        import sys
        import types
        import torch

        # shap_e.util.notebooks imports ipywidgets at module level for Jupyter
        # display helpers we don't use.  Stub it out so the import succeeds
        # in non-notebook environments.
        if "ipywidgets" not in sys.modules:
            sys.modules["ipywidgets"] = types.ModuleType("ipywidgets")
        from shap_e.util.notebooks import decode_latent_mesh

        device, xm, model, diffusion, sample_latents = self._model

        with torch.no_grad():
            latents = sample_latents(
                batch_size=1,
                model=model,
                diffusion=diffusion,
                guidance_scale=15.0,
                model_kwargs=dict(texts=[prompt]),
                progress=True,
                clip_denoised=True,
                use_fp16=False,   # MPS requires fp32
                use_karras=True,
                karras_steps=16,
                sigma_min=1e-3,
                sigma_max=160,
                s_churn=0,
            )

        if cancel.is_set():
            return None

        mesh = decode_latent_mesh(xm, latents[0]).tri_mesh()
        with open(out, "wb") as f:
            mesh.write_ply(f)

        return out.as_uri()
