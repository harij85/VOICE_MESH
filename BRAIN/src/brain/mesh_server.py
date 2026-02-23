"""Tiny HTTP server that serves generated PLY files with CORS headers."""
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import tempfile

SERVE_DIR = Path(tempfile.gettempdir()) / "voice_mesh_gen"
PORT = 8766


class _CORSHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SERVE_DIR), **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *args):
        pass  # suppress access logs


def start():
    SERVE_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", PORT), _CORSHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
