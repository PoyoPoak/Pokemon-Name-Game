"""Health / diagnostics endpoints.

Provides lightweight liveness & readiness checks plus process uptime.

Design:
  * GET /api/health          -> Combined status + uptime summary.
  * GET /api/health/live     -> Always returns 200 if process loop is alive.
  * GET /api/health/ready    -> Verifies critical dependencies (e.g. Redis).

All routes intentionally fast (< a few ms) and side‑effect free.
"""

from __future__ import annotations

import time
from typing import Dict, Any
from flask import Blueprint, jsonify
from util.route_builder import RouteBuilder

try:  # Redis is optional; readiness will reflect failure gracefully
    from config import Config  # type: ignore
    _redis = getattr(Config, "SESSION_REDIS", None)
except Exception:  # pragma: no cover - extremely defensive
    _redis = None

START_TIME = time.time()

bp = Blueprint("health", __name__)
__all__ = ["bp"]


def _uptime_payload() -> Dict[str, Any]:
    now = time.time()
    uptime_s = int(now - START_TIME)
    return {
        "uptimeSeconds": uptime_s,
        "uptime": {
            "days": uptime_s // 86400,
            "hours": (uptime_s // 3600) % 24,
            "minutes": (uptime_s // 60) % 60,
            "seconds": uptime_s % 60,
        },
        "processStart": int(START_TIME),
        "now": int(now),
    }


def health():
    """Aggregate liveness + readiness + uptime in one call."""
    live_status = "ok"  # If this code runs, process is live
    ready_ok = True
    checks: Dict[str, str] = {}

    # Dependency: Redis (session store)
    if _redis is not None:
        try:
            _redis.ping()
            checks["redis"] = "ok"
        except Exception as e:  # pragma: no cover
            checks["redis"] = f"error:{type(e).__name__}"
            ready_ok = False
    else:
        checks["redis"] = "unconfigured"

    status = "ok" if (live_status == "ok" and ready_ok) else "degraded"
    payload = {"status": status, "live": live_status, "ready": ready_ok, "checks": checks, **_uptime_payload()}
    code = 200 if status == "ok" else 503
    return jsonify(payload), code


def liveness():  # Always fast; no external calls
    return jsonify({"status": "ok", **_uptime_payload()})


def readiness():
    ready_ok = True
    checks: Dict[str, str] = {}
    if _redis is not None:
        try:
            _redis.ping()
            checks["redis"] = "ok"
        except Exception as e:  # pragma: no cover
            checks["redis"] = f"error:{type(e).__name__}"
            ready_ok = False
    else:
        checks["redis"] = "unconfigured"
    code = 200 if ready_ok else 503
    return jsonify({"status": "ok" if ready_ok else "degraded", "ready": ready_ok, "checks": checks}), code


RouteBuilder(bp) \
    .route("/health") \
    .methods("GET") \
    .handler(health) \
    .build()

RouteBuilder(bp) \
    .route("/health/live") \
    .methods("GET") \
    .handler(liveness) \
    .build()

RouteBuilder(bp) \
    .route("/health/ready") \
    .methods("GET") \
    .handler(readiness) \
    .build()
