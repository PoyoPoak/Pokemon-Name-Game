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
from flask_cors import CORS
from config import Config
from util.user import User
from util.lobby import Lobby


# ---------------------------------------------------------------------------
# App / extensions
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 megabytes
# Default secure cookie sessions (Flask built-in). Removed Flask-Session/Redis.

# CORS only in development when the UI runs on a different origin (e.g., localhost:3000)
if os.environ.get("FLASK_ENV") == "development":
    frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}}, supports_credentials=True)


# ---------------------------------------------------------------------------
# Blueprints (register additional ones here)
# ---------------------------------------------------------------------------
from routes.example_routes import bp as example_bp
from routes.health_routes import bp as health_bp
from routes.game_routes import bp as game_bp

app.register_blueprint(example_bp, url_prefix="/api")
app.register_blueprint(health_bp, url_prefix="/api")
app.register_blueprint(game_bp, url_prefix="/api")


# ---------------------------------------------------------------------------
# Static frontend (built SPA). In container, FRONTEND_DIST is copied in build.
# ---------------------------------------------------------------------------
FRONTEND_DIST = os.path.abspath(os.environ.get("FRONTEND_DIST", os.path.join(os.path.dirname(__file__), "..", "frontend_dist")))

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_spa(path: str):  # pragma: no cover (simple file serving)
    # Only handle non-API routes
    if path.startswith('api/'):
        abort(404)
    if os.path.isdir(FRONTEND_DIST):
        full_path = os.path.join(FRONTEND_DIST, path)
        if path and os.path.exists(full_path) and os.path.isfile(full_path):
            return send_from_directory(FRONTEND_DIST, path)
        index_path = os.path.join(FRONTEND_DIST, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(FRONTEND_DIST, 'index.html')
    return "Frontend build not found", 503


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
    
    if os.environ.get("FLASK_ENV") != "development" and os.environ.get("HEADLESS") != "1":
        open_browser(f"http://localhost:{port}/")
    
    print(app.url_map)

    app.run(host="localhost", port=port, debug=False)
