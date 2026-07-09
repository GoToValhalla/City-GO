#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.place import Place
from services.place_data_sanitizer import is_placeholder_enrichment_value

AUDITED_FIELDS = ("address", "opening_hours", "short_description")


def audit_placeholder_enrichment(db: Session, *, limit_ids: int = 100) -> dict[str, Any]:
    """Return a read-only report of known placeholder enrichment values.

    This function intentionally performs no writes. It is safe to call from tests and
    local diagnostics; production cleanup must be a separate explicit repair task.
    """

    fields: dict[str, dict[str, Any]] = {
        field: {"count": 0, "place_ids": []}
        for field in AUDITED_FIELDS
    }

    query = db.query(Place.id, Place.title, Place.address, Place.opening_hours, Place.short_description).order_by(Place.id.asc())
    for row in query.yield_per(500):
        title = str(row.title or "")
        values = {
            "address": row.address,
            "opening_hours": row.opening_hours,
            "short_description": row.short_description,
        }
        for field, value in values.items():
            if not is_placeholder_enrichment_value(field, value, title=title):
                continue
            entry = fields[field]
            entry["count"] += 1
            if len(entry["place_ids"]) < limit_ids:
                entry["place_ids"].append(row.id)

    total_matches = sum(int(payload["count"]) for payload in fields.values())
    return {
        "status": "ok",
        "mode": "read_only",
        "audited_fields": list(AUDITED_FIELDS),
        "total_matches": total_matches,
        "fields": fields,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit known fabricated City GO enrichment placeholder values")
    parser.add_argument("--limit-ids", type=int, default=100, help="Maximum matching place IDs to print per field")
    parser.add_argument("--json", action="store_true", help="Print JSON report")
    return parser.parse_args(argv)


def format_text_report(report: dict[str, Any]) -> str:
    lines = [
        "CITY GO · Placeholder enrichment audit",
        "Mode: read-only",
        f"Total placeholder matches: {report['total_matches']}",
        "",
        "Fields:",
    ]
    for field, payload in report["fields"].items():
        ids = ",".join(str(place_id) for place_id in payload["place_ids"]) or "-"
        lines.append(f"- {field}: count={payload['count']} sample_place_ids={ids}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    with SessionLocal() as db:
        report = audit_placeholder_enrichment(db, limit_ids=max(0, args.limit_ids))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_text_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
