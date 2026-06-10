"""Пути audit pack Алматы."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

_APP_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = _APP_ROOT / "data/audit/almaty_enrichment_audit_"
BATCHES_DIR = AUDIT_ROOT / "enrichment_batches_almaty"
CITY_SLUGS = ("алматы", "almaty")


def ensure_dirs() -> None:
    AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)


def stamp() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
