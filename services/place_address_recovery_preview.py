"""Preview apply-from-review без записи в БД."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from services.place_address_recovery_row import evaluate_review_row, sample


def preview_from_review(db: Session, csv_path: str | Path) -> dict[str, Any]:
    path = Path(csv_path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    stats: dict[str, Any] = {
        "mode": "preview_from_review",
        "csv": str(path),
        "checked_rows": 0,
        "would_apply": 0,
        "skipped_should_apply_false": 0,
        "skipped_existing_real_address": 0,
        "skipped_missing_place": 0,
        "skipped_empty_proposed": 0,
        "skipped_policy": 0,
        "errors": 0,
        "samples": {"would_apply": [], "skipped": [], "errors": []},
    }
    for row in rows:
        stats["checked_rows"] += 1
        outcome, detail, _place = evaluate_review_row(db, row)
        if outcome == "would_apply":
            stats["would_apply"] += 1
            sample(stats, "would_apply", row, detail)
            continue
        if outcome == "error":
            stats["errors"] += 1
            sample(stats, "errors", row, detail)
            continue
        stats[outcome] += 1
        sample(stats, "skipped", row, detail)
    return stats
