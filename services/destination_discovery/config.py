"""Discovery provider configuration."""

from __future__ import annotations

import os


def discovery_provider_name() -> str:
    return os.getenv("CITYGO_DISCOVERY_PROVIDER", "auto").strip().lower() or "auto"
