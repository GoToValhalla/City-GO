"""Экспорт review-артефактов address recovery."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

EXPORT_DIR = Path("data/exports/address_recovery")
CSV_FIELDS = (
    "place_id", "slug", "title", "category", "lat", "lng", "old_address",
    "proposed_address", "source", "confidence", "raw_display_name",
    "should_apply", "skip_reason", "comment",
)


def export_review(city_slug: str, rows: list[dict[str, object]], summary: dict[str, Any]) -> dict[str, str]:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = f"address_recovery_{city_slug}_{stamp}"
    csv_path = EXPORT_DIR / f"{base}.csv"
    json_path = EXPORT_DIR / f"{base}.json"
    _write_csv(csv_path, rows)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"csv": str(csv_path), "json": str(json_path)}


def build_summary(city_slug: str, rows: list[dict[str, object]], errors: int, http_403: int) -> dict[str, Any]:
    recoverable = sum(1 for row in rows if row.get("proposed_address"))
    should_apply = sum(1 for row in rows if row.get("should_apply"))
    skipped_generic = sum(1 for row in rows if row.get("skip_reason") == "generic")
    by_category = dict(Counter(str(row.get("category") or "") for row in rows))
    confidence = dict(Counter(str(row.get("confidence") or "none") for row in rows))
    return {
        "city": city_slug,
        "checked": len(rows),
        "recoverable": recoverable,
        "should_apply_count": should_apply,
        "skipped_generic": skipped_generic,
        "skipped_errors": errors,
        "http_403_count": http_403,
        "by_category": by_category,
        "confidence_breakdown": confidence,
        "errors": [row for row in rows if row.get("skip_reason") == "error"],
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})
