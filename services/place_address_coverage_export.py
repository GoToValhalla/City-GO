"""Сохранение JSON-артефактов address coverage."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

EXPORT_DIR = Path("data/exports/address_recovery")


def export_coverage(cities: dict[str, Any], *, label: str = "address_coverage") -> str:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / f"{label}_{stamp}.json"
    payload = {"generated_at": stamp, "cities": cities}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return str(path)
