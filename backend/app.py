"""Application entry point for backend.

This module intentionally serves BOTH:
  * JSON API under /api/* (Flask blueprints)
  * Built SPA assets (catch‑all route returning index.html for client routing)

In development, a separate Vite dev server (e.g. :3000) can be used; in a
packaged / production deployment (PyInstaller), the static build is bundled
and served from FRONTEND_DIR on the same port as the API.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from flask import Flask, send_from_directory, abort
from flask_session import Session
from flask_cors import CORS
from config import Config


# ---------------------------------------------------------------------------
# Path / build helpers
# ---------------------------------------------------------------------------
HERE = os.path.abspath(os.path.dirname(__file__))
if hasattr(sys, "_MEIPASS"):
    # Running from the PyInstaller bundle
    FRONTEND_DIR = os.path.join(sys._MEIPASS, "frontend", "dist")
else:
    # Running from source:./frontend/dist
    FRONTEND_DIR = os.path.abspath(os.path.join(HERE, "..", "frontend", "dist"))


def resource_path(*parts: str) -> str:
    """Return an absolute path to a bundled resource or project file.

    When frozen (PyInstaller), resources live inside the temporary _MEIPASS dir;
    otherwise fall back to the source tree location (HERE).
    """
    base = getattr(sys, "_MEIPASS", HERE)  # type: ignore[attr-defined]
    return os.path.join(base, *parts)


try:
    if hasattr(sys, "_MEIPASS"):  # only true in the PyInstaller bundle
        os.add_dll_directory(os.path.join(sys._MEIPASS, "ortools", ".libs"))
except Exception:
    pass


# ---------------------------------------------------------------------------
# App / extensions
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 megabytes
Session(app)

# CORS only in development when the UI runs on a different origin (e.g., localhost:3000)
if os.environ.get("FLASK_ENV") == "development":
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}}, supports_credentials=True)


# ---------------------------------------------------------------------------
# Blueprints (register additional ones here)
# ---------------------------------------------------------------------------
from routes.example_routes import bp as example_bp
app.register_blueprint(example_bp, url_prefix="/api")


# ---------------------------------------------------------------------------
# Static / SPA fallback route
# ---------------------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path: str):  # type: ignore[override]
    """Serve built frontend assets or fall back to index.html for client routing.

    Ensures we DO NOT swallow API routes so that 404 bubbles and blueprint
    routes under /api/* remain authoritative.
    """
    # Never intercept API routes (let blueprint routing / 404 handling act)
    if path and path.startswith("api/"):
        abort(404)

    # Serve a real static asset if it exists
    file_path = os.path.join(FRONTEND_DIR, path)
    if path and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(FRONTEND_DIR, path)

    # SPA fallback
    return send_from_directory(FRONTEND_DIR, "index.html")


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def open_browser(url: str, delay: float = 1.0) -> None:
    """Open the default system browser to the provided URL (non-blocking)."""

    def _open():  # noqa: D401
        webbrowser.open(url)

    threading.Timer(delay, _open).start()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Only auto-open in packaged / non-dev usage (avoid tab spam during dev)
    if os.environ.get("FLASK_ENV") != "development" and os.environ.get("HEADLESS") != "1":
        open_browser(f"http://localhost:{port}/")
    print(app.url_map)  # List all registered routes
    app.run(host="localhost", port=port, debug=False)
