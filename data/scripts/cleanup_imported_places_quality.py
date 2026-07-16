from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from models.city import City
from models.place import Place
from models.place_source_presence import PlaceSourcePresence
from services.place_import_lifecycle_service import (
    REMOVED_FROM_SOURCE_STATUS,
    existing_place_must_be_hidden,
    hide_place,
)
from services.review_queue_service import ensure_review_item

BAD_TITLE_VALUES = {
    "yes",
    "no",
    "none",
    "null",
    "unknown",
    "fixme",
    "todo",
    "n/a",
    "na",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", action="append")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--sample-limit", type=int, default=20)
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)

    if args.dry_run == args.apply:
        raise SystemExit("Choose exactly one of --dry-run or --apply")

    with SessionLocal() as db:
        cities = _load_cities(db, args.city)

        if not cities:
            raise SystemExit("No cities found for cleanup")

        results = []

        for city in cities:
            results.append(
                _cleanup_city(
                    db=db,
                    city=city,
                    apply=args.apply,
                    sample_limit=args.sample_limit,
                )
            )

        if args.apply:
            db.commit()

        return {
            "mode": "apply" if args.apply else "dry_run",
            "city_count": len(cities),
            "results": results,
        }


def _load_cities(db, city_slugs: list[str] | None) -> list[City]:
    query = db.query(City)

    if city_slugs:
        query = query.filter(City.slug.in_(city_slugs))

    return query.order_by(City.name.asc()).all()


def _cleanup_city(
    db,
    city: City,
    apply: bool,
    sample_limit: int,
) -> dict[str, Any]:
    places = (
        db.query(Place)
        .filter(Place.city_id == city.id)
        .order_by(Place.id.asc())
        .all()
    )

    reason_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    samples: list[dict[str, Any]] = []

    total_places = len(places)
    active_before = 0
    public_bad_places = 0
    already_hidden_bad_places = 0
    hidden_applied = 0
    review_flagged = 0

    for place in places:
        category_counter[str(place.category or "none")] += 1
        status_counter[str(place.status or "none")] += 1

        if place.is_active and place.status == "active":
            active_before += 1

        reason = _cleanup_reason(db=db, place=place)
        if reason is None:
            continue

        reason_counter[reason] += 1

        is_published = bool(place.is_published)
        if place.is_active:
            public_bad_places += 1
        else:
            already_hidden_bad_places += 1

        if len(samples) < sample_limit:
            samples.append(
                {
                    "id": place.id,
                    "slug": place.slug,
                    "title": place.title,
                    "category": place.category,
                    "status": place.status,
                    "is_active": place.is_active,
                    "is_published": is_published,
                    "reason": reason,
                }
            )

        if not apply:
            continue

        # CITYGO-341/CITYGO-344: a published place must never be unpublished
        # by an automated quality-cleanup pass. Flag it for admin review with
        # full evidence instead; only an unpublished (not yet live) bad place
        # may actually be hidden here.
        if is_published:
            ensure_review_item(
                db,
                city_id=city.id,
                place_id=place.id,
                job_id=None,
                field_name="quality_cleanup",
                reason=reason,
                severity="high",
                payload={
                    "kind": "quality_cleanup_flag",
                    "place_status": place.status,
                    "place_category": place.category,
                },
            )
            review_flagged += 1
        elif place.is_active:
            status = _target_status_for_reason(reason)
            hide_place(
                place=place,
                reason=reason,
                status=status,
            )
            hidden_applied += 1

    return {
        "city": city.slug,
        "total_places": total_places,
        "active_before": active_before,
        "bad_places_total": public_bad_places + already_hidden_bad_places,
        "bad_places_public": public_bad_places,
        "bad_places_already_hidden": already_hidden_bad_places,
        "hidden_applied": hidden_applied,
        "review_flagged": review_flagged,
        "reasons": dict(reason_counter),
        "categories": dict(category_counter),
        "statuses": dict(status_counter),
        "samples": samples,
    }


def _cleanup_reason(db, place: Place) -> str | None:
    if place.category == "transport":
        return "transport_category"

    if _is_bad_title(place.title):
        return "bad_title"

    if existing_place_must_be_hidden(place):
        return "existing_place_must_be_hidden"

    max_missing_count = _max_consecutive_missing_count(db=db, place_id=place.id)

    if max_missing_count >= 3:
        return "missing_from_source_repeatedly"

    return None


def _max_consecutive_missing_count(db, place_id: int) -> int:
    rows = (
        db.query(PlaceSourcePresence)
        .filter(PlaceSourcePresence.place_id == place_id)
        .all()
    )

    if not rows:
        return 0

    return max(row.consecutive_missing_count or 0 for row in rows)


def _target_status_for_reason(reason: str) -> str:
    if reason == "missing_from_source_repeatedly":
        return REMOVED_FROM_SOURCE_STATUS

    return "draft"


def _is_bad_title(value: str | None) -> bool:
    if value is None:
        return True

    normalized = str(value).lower().strip()
    compact = "".join(normalized.split())

    if not compact:
        return True

    if compact in BAD_TITLE_VALUES:
        return True

    numeric_candidate = normalized
    for char in ["№", "#", " ", ",", ".", ";", ":", "|", "/", "\\", "-", "–", "—", "_", "(", ")", "+"]:
        numeric_candidate = numeric_candidate.replace(char, "")

    if numeric_candidate.isdigit():
        return True

    return False


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
