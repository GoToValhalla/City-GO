#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from db.session import SessionLocal
from models.place import Place
from services.admin_coverage_place_checks import place_has_coverage_address
from services.place_quality_signals import is_placeholder_title
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES, evaluate_place_route_eligibility


def main() -> int:
    with SessionLocal() as db:
        places = db.query(Place).all()
        report = build_report(places)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def build_report(places: list[Place]) -> dict[str, object]:
    verdicts = [(place, evaluate_place_route_eligibility(place)) for place in places]
    reasons = Counter(reason for _place, verdict in verdicts for reason in verdict.reasons)
    by_city: dict[str, Counter[str]] = defaultdict(Counter)
    for place, verdict in verdicts:
        key = str(getattr(place, "city_id", "unknown") or "unknown")
        by_city[key]["eligible" if verdict.eligible else "excluded"] += 1
        for reason in verdict.reasons[:1] or ("eligible",):
            by_city[key][reason] += 1
    return {
        "route_eligible_count": sum(1 for _place, verdict in verdicts if verdict.eligible),
        "route_excluded_count": sum(1 for _place, verdict in verdicts if not verdict.eligible),
        "route_unknown_count": sum(1 for _place, verdict in verdicts if "unknown_category" in verdict.reasons),
        "generic_osm_count": sum(1 for place in places if is_placeholder_title(place.title)),
        "medical_service_currently_eligible_count": sum(1 for place in places if _category(place) in HARD_EXCLUDED_CATEGORIES and place.is_route_eligible is True),
        "published_without_photo": sum(1 for place in places if place.is_published is True and not place.image_url),
        "missing_bad_address": sum(1 for place in places if not place_has_coverage_address(place)),
        "breakdown_by_exclusion_reason": dict(reasons),
        "sql_policy_vs_python_policy_drift_count": sum(1 for place, verdict in verdicts if bool(place.is_route_eligible) != verdict.eligible),
        "by_city": {city: dict(counter) for city, counter in by_city.items()},
    }


def _category(place: Place) -> str:
    return str(getattr(place, "canonical_category", None) or getattr(getattr(place, "category_ref", None), "code", "") or "").strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
