"""System logs CSV для Алматы."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.system_log import SystemLog

MODULES = ("import", "address", "enrichment", "image", "route", "dry_run", "scheduler", "cron", "city_import")


def write_system_logs(db: Session, out: Path, slugs: tuple[str, ...], limit: int = 5000) -> int:
    slug_filter = or_(*[SystemLog.city_slug == s for s in slugs], SystemLog.city_slug.is_(None))
    mod_filter = or_(*[SystemLog.module == m for m in MODULES], SystemLog.module.like("%import%"))
    rows = (
        db.query(SystemLog)
        .filter(slug_filter, mod_filter)
        .order_by(SystemLog.created_at.desc())
        .limit(limit)
        .all()
    )
    fields = [
        "created_at", "level", "module", "message", "details_json",
        "city_slug", "place_id", "route_id", "request_id",
    ]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({
                "created_at": r.created_at, "level": r.level, "module": r.module,
                "message": r.message,
                "details_json": json.dumps(r.details, ensure_ascii=False) if r.details else None,
                "city_slug": r.city_slug, "place_id": r.place_id,
                "route_id": r.route_id, "request_id": r.request_id,
            })
    return len(rows)
