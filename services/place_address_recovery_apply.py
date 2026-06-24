"""Применение адресов из review CSV без повторного geocoding."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.place_address_recovery_row import evaluate_review_row, sample
from services.place_import_lifecycle_service import mark_place_for_review


def apply_from_review(db: Session, csv_path: str | Path) -> dict[str, Any]:
    path = Path(csv_path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    stats = _empty_stats(path)
    for row in rows:
        _apply_row(db, row, stats)
    stats["result_json"] = _write_result(path, stats)
    return stats


def _empty_stats(path: Path) -> dict[str, Any]:
    return {
        "mode": "apply_from_review",
        "csv": str(path),
        "checked_rows": 0,
        "applied": 0,
        "skipped_should_apply_false": 0,
        "skipped_existing_real_address": 0,
        "skipped_missing_place": 0,
        "skipped_empty_proposed": 0,
        "skipped_policy": 0,
        "errors": 0,
        "samples": {"applied": [], "skipped": [], "errors": []},
    }


def _apply_row(db: Session, row: dict[str, str], stats: dict[str, Any]) -> None:
    stats["checked_rows"] += 1
    outcome, detail, place = evaluate_review_row(db, row)
    if outcome != "would_apply" or place is None:
        if outcome == "error":
            stats["errors"] += 1
            sample(stats, "errors", row, detail)
            return
        if outcome != "would_apply":
            stats[outcome] += 1
            sample(stats, "skipped", row, detail)
        return
    try:
        place.address = detail
        place.address_source = str(row.get("source") or "address_recovery")[:64]
        place.address_confidence = _float_or_none(row.get("provider_confidence"))
        place.address_updated_at = datetime.utcnow()
        mark_place_for_review(place, reason="address_recovered")
        db.add(place)
        db.commit()
        stats["applied"] += 1
        sample(stats, "applied", row, detail)
    except Exception as exc:
        db.rollback()
        stats["errors"] += 1
        sample(stats, "errors", row, str(exc))


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value not in {None, ""} else None
    except (TypeError, ValueError):
        return None


def _write_result(csv_path: Path, stats: dict[str, Any]) -> str:
    out = csv_path.with_suffix(csv_path.suffix + ".apply_result.json")
    payload = {key: value for key, value in stats.items() if key != "result_json"}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)
