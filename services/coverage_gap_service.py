from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
KNOWN_POI_SEED_PATH = ROOT_DIR / "data" / "config" / "known_missing_poi.json"
IMPORT_TARGETS_PATH = ROOT_DIR / "data" / "config" / "import_targets.json"


def load_known_poi_seed(path: Path = KNOWN_POI_SEED_PATH) -> list[dict[str, Any]]:
    """Loads repository seed records for must-have POI coverage checks."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        {**item, "city_slug": city["city"]}
        for city in payload.get("cities", [])
        for item in city.get("items", [])
    ]


def build_coverage_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    status: str | None = None,
    gap_reason: str | None = None,
    expected_category: str | None = None,
    offset: int = 0,
    limit: int = 100,
) -> dict[str, Any]:
    """Builds a first admin-ready coverage report from seed records.

    This first layer intentionally does not mutate production data. It explains
    whether a seed POI is covered by any configured import scope and exposes the
    result through admin API. Matching with imported places is the next step.
    """

    items = load_known_poi_seed()
    if city_slug:
        items = [item for item in items if item["city_slug"] == city_slug]

    evaluated = [_evaluate_seed(item) for item in items]
    if status:
        evaluated = [item for item in evaluated if item["status"] == status]
    if gap_reason:
        evaluated = [item for item in evaluated if item.get("gap_reason") == gap_reason]
    if expected_category:
        evaluated = [item for item in evaluated if item["expected_category"] == expected_category]

    total = len(evaluated)
    page_items = evaluated[offset: offset + limit]
    return {
        "items": page_items,
        "total": total,
        "offset": offset,
        "limit": limit,
        "summary": {
            "total": total,
            "by_status": dict(Counter(item["status"] for item in evaluated)),
            "by_gap_reason": dict(Counter(item.get("gap_reason") or "none" for item in evaluated)),
            "by_expected_category": dict(Counter(item["expected_category"] for item in evaluated)),
            "unresolved": sum(1 for item in evaluated if item["status"] != "matched"),
        },
    }


def _evaluate_seed(seed: dict[str, Any]) -> dict[str, Any]:
    inside_scope = _point_is_inside_any_import_scope(seed)
    status = seed.get("status") or "missing"
    gap_reason = None if inside_scope else "outside_bbox"
    if not inside_scope:
        status = "out_of_scope"

    return {
        "city_slug": seed["city_slug"],
        "slug": seed["slug"],
        "name": seed.get("name_ru") or seed.get("name_en") or seed["slug"],
        "name_en": seed.get("name_en"),
        "name_ru": seed.get("name_ru"),
        "lat": seed["lat"],
        "lng": seed["lng"],
        "coordinate_precision": seed.get("coordinate_precision", "approximate"),
        "expected_category": seed["expected_category"],
        "expected_scope": seed["expected_scope"],
        "expected_route_policy": seed.get("expected_route_policy", "must_have"),
        "significance": seed.get("significance", "local"),
        "status": status,
        "gap_reason": gap_reason,
        "matched_place_id": None,
        "matched_place_title": None,
        "matched_place_slug": None,
    }


def _point_is_inside_any_import_scope(seed: dict[str, Any]) -> bool:
    payload = json.loads(IMPORT_TARGETS_PATH.read_text(encoding="utf-8"))
    for city in payload.get("targets", []):
        if city.get("city") != seed["city_slug"]:
            continue
        for scope in city.get("scopes", []):
            if _bbox_contains(scope.get("bbox") or {}, lat=seed["lat"], lng=seed["lng"]):
                return True
    return False


def _bbox_contains(bbox: dict[str, Any], *, lat: float, lng: float) -> bool:
    try:
        return float(bbox["south"]) <= lat <= float(bbox["north"]) and float(bbox["west"]) <= lng <= float(bbox["east"])
    except (KeyError, TypeError, ValueError):
        return False
