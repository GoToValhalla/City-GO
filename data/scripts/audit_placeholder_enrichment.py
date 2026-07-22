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
from models.place_field_confidence import PlaceFieldConfidence
from services.place_data_sanitizer import is_placeholder_enrichment_value

AUDITED_FIELDS = ("address", "opening_hours", "short_description", "atmosphere", "inside", "best_for")

# CITYGO-265: the exact source_type tag the now-removed _apply_category_profile()
# (services/place_enrichment_sources.py) wrote to place_field_confidence for
# every fabricated atmosphere/inside/best_for value -- a durable, unambiguous
# marker for historical rows, independent of the text-pattern match above
# (which only catches the fields while they still hold the exact fabricated
# string; a place could have since had that field edited by an admin while
# the confidence row from the fabrication event is still on record).
FABRICATED_CATEGORY_RULES_SOURCE_TYPE = "citygo_category_rules"

# CITYGO-265: the now-removed _visit_duration()/_price_level() per-category
# lookup tables (data/scripts/import_city_osm.py). No lineage/confidence row
# was ever recorded for these two fields, so an exact-value-per-category match
# is the best available historical signal -- necessarily a heuristic, not
# proof, since a genuine value could coincidentally equal the same number.
_FORMER_VISIT_DURATION_BY_CATEGORY: dict[str, int] = {
    "cafe": 30, "food": 60, "museum": 75, "culture": 45, "viewpoint": 20,
    "park": 45, "beach": 60, "walk": 45, "useful": 10, "health": 10,
}
_FORMER_VISIT_DURATION_DEFAULT = 30
_FORMER_PRICE_LEVEL_BY_CATEGORY: dict[str, int] = {
    "park": 0, "beach": 0, "walk": 0, "viewpoint": 0, "culture": 1,
    "museum": 1, "useful": 1, "health": 1, "cafe": 2, "food": 2,
}
_FORMER_PRICE_LEVEL_DEFAULT = 1


def _matches_former_category_lookup(category: str | None, value: object, *, by_category: dict[str, int], default: int) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    expected = by_category.get(str(category or "").strip().lower(), default)
    return int(value) == expected


def audit_placeholder_enrichment(db: Session, *, limit_ids: int = 100) -> dict[str, Any]:
    """Return a read-only report of known placeholder/fabricated enrichment values.

    This function intentionally performs no writes. It is safe to call from tests and
    local diagnostics; production cleanup must be a separate explicit repair task.

    Covers two distinct kinds of historical fabrication (CITYGO-265):
    1. Free-text placeholders (address/opening_hours/short_description) and the
       exact fixed category-template strings formerly written to
       atmosphere/inside/best_for -- detected via is_placeholder_enrichment_value,
       an exact/pattern text match.
    2. average_visit_duration_minutes/price_level rows that exactly match the
       now-removed per-category lookup tables -- a heuristic flag, not proof,
       surfaced separately under "suspected_category_lookup_fields" since a
       false positive is possible (a genuine value could equal the same
       number by coincidence).
    """

    fields: dict[str, dict[str, Any]] = {
        field: {"count": 0, "place_ids": []}
        for field in AUDITED_FIELDS
    }
    suspected_lookup_fields: dict[str, dict[str, Any]] = {
        field: {"count": 0, "place_ids": []}
        for field in ("average_visit_duration_minutes", "price_level")
    }

    query = db.query(
        Place.id, Place.title, Place.category, Place.canonical_category,
        Place.address, Place.opening_hours, Place.short_description,
        Place.atmosphere, Place.inside, Place.best_for,
        Place.average_visit_duration_minutes, Place.price_level,
    ).order_by(Place.id.asc())
    for row in query.yield_per(500):
        title = str(row.title or "")
        values = {
            "address": row.address,
            "opening_hours": row.opening_hours,
            "short_description": row.short_description,
            "atmosphere": row.atmosphere,
            "inside": row.inside,
            "best_for": row.best_for,
        }
        for field, value in values.items():
            if not is_placeholder_enrichment_value(field, value, title=title):
                continue
            entry = fields[field]
            entry["count"] += 1
            if len(entry["place_ids"]) < limit_ids:
                entry["place_ids"].append(row.id)

        category = row.canonical_category or row.category
        if _matches_former_category_lookup(category, row.average_visit_duration_minutes, by_category=_FORMER_VISIT_DURATION_BY_CATEGORY, default=_FORMER_VISIT_DURATION_DEFAULT):
            entry = suspected_lookup_fields["average_visit_duration_minutes"]
            entry["count"] += 1
            if len(entry["place_ids"]) < limit_ids:
                entry["place_ids"].append(row.id)
        if _matches_former_category_lookup(category, row.price_level, by_category=_FORMER_PRICE_LEVEL_BY_CATEGORY, default=_FORMER_PRICE_LEVEL_DEFAULT):
            entry = suspected_lookup_fields["price_level"]
            entry["count"] += 1
            if len(entry["place_ids"]) < limit_ids:
                entry["place_ids"].append(row.id)

    confidence_query = (
        db.query(PlaceFieldConfidence.place_id, PlaceFieldConfidence.field_name)
        .filter(PlaceFieldConfidence.source_type == FABRICATED_CATEGORY_RULES_SOURCE_TYPE)
        .order_by(PlaceFieldConfidence.place_id.asc())
    )
    fabricated_confidence_rows: dict[str, dict[str, Any]] = {}
    for confidence_row in confidence_query.yield_per(500):
        entry = fabricated_confidence_rows.setdefault(confidence_row.field_name, {"count": 0, "place_ids": []})
        entry["count"] += 1
        if len(entry["place_ids"]) < limit_ids:
            entry["place_ids"].append(confidence_row.place_id)

    total_matches = sum(int(payload["count"]) for payload in fields.values())
    total_suspected = sum(int(payload["count"]) for payload in suspected_lookup_fields.values())
    total_fabricated_confidence = sum(int(payload["count"]) for payload in fabricated_confidence_rows.values())
    return {
        "status": "ok",
        "mode": "read_only",
        "audited_fields": list(AUDITED_FIELDS),
        "total_matches": total_matches,
        "fields": fields,
        "suspected_category_lookup_fields": suspected_lookup_fields,
        "total_suspected_category_lookup_matches": total_suspected,
        "fabricated_confidence_source_type": FABRICATED_CATEGORY_RULES_SOURCE_TYPE,
        "fabricated_confidence_rows": fabricated_confidence_rows,
        "total_fabricated_confidence_rows": total_fabricated_confidence,
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

    lines.append("")
    lines.append(f"Suspected former category-lookup matches (heuristic, not proof): {report['total_suspected_category_lookup_matches']}")
    for field, payload in report["suspected_category_lookup_fields"].items():
        ids = ",".join(str(place_id) for place_id in payload["place_ids"]) or "-"
        lines.append(f"- {field}: count={payload['count']} sample_place_ids={ids}")

    lines.append("")
    lines.append(f"place_field_confidence rows tagged source_type={report['fabricated_confidence_source_type']!r}: {report['total_fabricated_confidence_rows']}")
    for field, payload in report["fabricated_confidence_rows"].items():
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
