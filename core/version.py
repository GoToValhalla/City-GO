"""Build/version metadata for runtime diagnostics."""

from __future__ import annotations

import os


def _read_env(name: str, fallback: str = "unknown") -> str:
    """Return a normalized environment value for public diagnostics."""
    value = os.getenv(name, "").strip()
    return value or fallback


def get_backend_version() -> dict[str, str]:
    """Return backend build metadata baked into the Docker image."""
    build_sha = _read_env("CITY_GO_BUILD_SHA", "local")
    return {
        "service": "backend",
        "version": _read_env("CITY_GO_APP_VERSION", "0.1.0"),
        "build_sha": build_sha,
        "build_sha_short": build_sha[:7] if build_sha and build_sha != "unknown" else "unknown",
        "build_run_id": _read_env("CITY_GO_BUILD_RUN_ID", "local"),
        "build_run_number": _read_env("CITY_GO_BUILD_RUN_NUMBER", "local"),
        "build_time": _read_env("CITY_GO_BUILD_TIME", "local"),
    }
