from __future__ import annotations

import json
import math
import re
from collections import Counter
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from models.city import City
from models.known_missing_poi import KnownMissingPoi
from models.place import Place
from models.source_observation import SourceObservation
from services.osm_import_taxonomy import unsupported_tag_reason

ROOT_DIR = Path(__file__).resolve().parents[1]
KNOWN_POI_SEED_PATH = ROOT_DIR / "data" / "config" / "known_missing_poi.json"
IMPORT_TARGETS_PATH = ROOT_DIR / "data" / "config" / "import_targets.json"

MATCHED_STATUSES = {"matched"}
UNRESOLVED_STATUSES = {
    "missing",
    "needs_review",
    "source_absent",
    "out_of_scope",
    "tag_unsupported",
    "rejected_policy",
    "duplicate",
}
CRITICAL_POLICIES = {"must_have", "day_trip"}

CATEGORY_COMPATIBILITY: dict[str, set[str]] = {
    "culture": {"culture", "museum", "viewpoint"},
    "food": {"food", "cafe"},
    "walk": {"walk", "park", "beach", "viewpoint", "culture"},
    "park": {"park", "walk"},
    "cafe": {"cafe", "food"},
}

REJECTION_REASON_TO_GAP: dict[str, tuple[str, str]] = {
    "unsupported_category": ("tag_unsupported", "unsupported_tag"),
    "hidden_category": ("rejected_policy", "hidden_by_policy"),
    "missing_name": ("needs_review", "missing_name"),
    "bad_name": ("needs_review", "missing_name"),
    "missing_coordinates": ("needs_review", "missing_coordinates"),
    "source_closed": ("rejected_policy", "hidden_by_policy"),
    "source_temporarily_closed": ("needs_review", "hidden_by_policy"),
    "source_removed_from_source": ("source_absent", "source_absent"),
}


def load_known_poi_seed(path: Path = KNOWN_POI_SEED_PATH) -> list[dict[str, Any]]:
    """Loads repository seed records for must-have POI coverage checks."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        {**item, "city_slug": city["city"]}
        for city in payload.get("cities", [])
        for item in city.get("items", [])
    ]


def sync_known_missing_poi_seed(db: Session, *, city_slug: str | None = None) -> dict[str, int]:
    """Upserts repository seed records into the persistent coverage registry.

    The seed file is a versioned source of truth for known must-have POI. The DB
    table is the operational state: admin review, matched place, status and notes.
    """

    created = 0
    updated = 0
    skipped_missing_city = 0
    now = datetime.utcnow()

    for seed in load_known_poi_seed():
        if city_slug and seed["city_slug"] != city_slug:
            continue

        city = db.query(City).filter(City.slug == seed["city_slug"]).first()
        if city is None:
            skipped_missing_city += 1
            continue

        row = (
            db.query(KnownMissingPoi)
            .filter(KnownMissingPoi.city_id == city.id, KnownMissingPoi.slug == seed["slug"])
            .first()
        )
        if row is None:
            row = KnownMissingPoi(city_id=city.id, slug=seed["slug"], lat=float(seed["lat"]), lng=float(seed["lng"]))
            db.add(row)
            created += 1
        else:
            updated += 1

        _apply_seed_to_row(row, seed, now)

    db.flush()
    return {"created": created, "updated": updated, "skipped_missing_city": skipped_missing_city}


def refresh_coverage_statuses(db: Session, *, city_slug: str | None = None) -> dict[str, Any]:
    """Refreshes persistent gap statuses by matching registry rows to current data."""

    sync_result = sync_known_missing_poi_seed(db, city_slug=city_slug)
    query = db.query(KnownMissingPoi).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)

    items = query.all()
    now = datetime.utcnow()
    changed = 0

    for row in items:
        evaluated = _evaluate_row(db, row)
        if _row_needs_update(row, evaluated):
            changed += 1
        row.status = evaluated["status"]
        row.gap_reason = evaluated.get("gap_reason")
        row.matched_place_id = evaluated.get("matched_place_id")
        row.review_notes = evaluated.get("review_notes")
        row.last_checked_at = now
        row.resolved_at = now if evaluated["status"] == "matched" else None
        row.updated_at = now

    db.flush()
    return {
        "synced": sync_result,
        "evaluated": len(items),
        "changed": changed,
        "summary": _summary_from_rows(items),
    }


def build_coverage_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    status: str | None = None,
    gap_reason: str | None = None,
    expected_category: str | None = None,
    offset: int = 0,
    limit: int = 100,
    refresh: bool = True,
) -> dict[str, Any]:
    """Builds an admin-ready coverage report from persistent registry rows."""

    if refresh:
        refresh_coverage_statuses(db, city_slug=city_slug)
        db.commit()

    query = db.query(KnownMissingPoi).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    if status:
        query = query.filter(KnownMissingPoi.status == status)
    if gap_reason:
        query = query.filter(KnownMissingPoi.gap_reason == gap_reason)
    if expected_category:
        query = query.filter(KnownMissingPoi.expected_category == expected_category)

    all_rows = query.order_by(City.slug.asc(), KnownMissingPoi.significance.desc(), KnownMissingPoi.slug.asc()).all()
    page_rows = all_rows[offset: offset + limit]

    return {
        "items": [_row_to_api_item(row) for row in page_rows],
        "total": len(all_rows),
        "offset": offset,
        "limit": limit,
        "summary": _summary_from_rows(all_rows),
        "filters": {
            "city_slug": city_slug,
            "status": status,
            "gap_reason": gap_reason,
            "expected_category": expected_category,
        },
    }


def _apply_seed_to_row(row: KnownMissingPoi, seed: dict[str, Any], now: datetime) -> None:
    # Keep admin review fields and matched_place_id, but refresh source-of-truth metadata.
    row.name_local = seed.get("name_local")
    row.name_en = seed.get("name_en")
    row.name_ru = seed.get("name_ru")
    row.lat = float(seed["lat"])
    row.lng = float(seed["lng"])
    row.coordinate_precision = seed.get("coordinate_precision") or "approximate"
    row.expected_category = seed["expected_category"]
    row.expected_scope = seed["expected_scope"]
    row.expected_route_policy = seed.get("expected_route_policy") or "must_have"
    row.significance = seed.get("significance") or "local"
    row.source = seed.get("source") or "manual_seed"
    row.external_refs = seed.get("external_refs") or []
    row.reporter_note = seed.get("reporter_note")
    row.updated_at = now


def _evaluate_row(db: Session, row: KnownMissingPoi) -> dict[str, Any]:
    matched_place, match_meta = _find_matching_place(db, row)
    if matched_place is not None:
        status, reason = _status_for_matched_place(row, matched_place)
        return {
            "status": status,
            "gap_reason": reason,
            "matched_place_id": matched_place.id,
            "review_notes": _review_note(status, reason, match_meta),
        }

    observation, observation_distance = _find_nearby_observation(db, row)
    if observation is not None:
        status, reason = _status_for_observation(observation)
        return {
            "status": status,
            "gap_reason": reason,
            "matched_place_id": None,
            "review_notes": f"Nearest source observation #{observation.id}, distance={observation_distance:.0f}m, reason={observation.rejection_reason or 'none'}",
        }

    if not _point_is_inside_any_import_scope(_row_as_seed(row)):
        return {
            "status": "out_of_scope",
            "gap_reason": "outside_bbox",
            "matched_place_id": None,
            "review_notes": "Point is outside configured import scopes for the city.",
        }

    return {
        "status": "source_absent",
        "gap_reason": "source_absent",
        "matched_place_id": None,
        "review_notes": "No matching place or source observation found inside configured import scopes.",
    }


def _find_matching_place(db: Session, row: KnownMissingPoi) -> tuple[Place | None, dict[str, Any]]:
    if row.matched_place_id:
        place = db.query(Place).filter(Place.id == row.matched_place_id).first()
        if place is not None:
            return place, {"source": "manual_match", "distance_m": _distance_m(row.lat, row.lng, place.lat, place.lng), "name_score": 1.0}

    places = db.query(Place).filter(Place.city_id == row.city_id).all()
    best: tuple[float, Place, dict[str, Any]] | None = None
    max_distance = _max_match_distance_m(row.expected_category)

    for place in places:
        distance = _distance_m(row.lat, row.lng, place.lat, place.lng)
        if distance > max_distance:
            continue

        category_match = _category_matches(row.expected_category, place.category or place.canonical_category)
        name_score = _best_name_score(_candidate_names(row), [place.title, place.slug])
        source_match = _place_matches_external_ref(place, row.external_refs or [])

        if not source_match and not category_match and name_score < 0.34 and distance > 45:
            continue

        score = (2.0 if source_match else 0.0) + (0.65 if category_match else 0.0) + name_score + max(0.0, 1.0 - distance / max_distance)
        meta = {
            "source": "auto_match",
            "distance_m": round(distance, 1),
            "name_score": round(name_score, 3),
            "category_match": category_match,
            "source_match": source_match,
        }
        if best is None or score > best[0]:
            best = (score, place, meta)

    if best is None:
        return None, {}
    return best[1], best[2]


def _find_nearby_observation(db: Session, row: KnownMissingPoi) -> tuple[SourceObservation | None, float]:
    observations = (
        db.query(SourceObservation)
        .filter(SourceObservation.city_id == row.city_id, SourceObservation.raw_lat.isnot(None), SourceObservation.raw_lng.isnot(None))
        .order_by(SourceObservation.id.desc())
        .limit(500)
        .all()
    )
    best: tuple[SourceObservation, float] | None = None
    max_distance = _max_match_distance_m(row.expected_category)

    for observation in observations:
        if observation.raw_lat is None or observation.raw_lng is None:
            continue
        distance = _distance_m(row.lat, row.lng, observation.raw_lat, observation.raw_lng)
        if distance > max_distance:
            continue
        if best is None or distance < best[1]:
            best = (observation, distance)

    return best if best is not None else (None, 0.0)


def _status_for_matched_place(row: KnownMissingPoi, place: Place) -> tuple[str, str | None]:
    if place.is_duplicate_suspected:
        return "duplicate", "duplicate_candidate"
    if not place.is_active or place.lifecycle_status not in {"active", "draft"}:
        return "rejected_policy", "hidden_by_policy"
    if not place.is_visible_in_catalog:
        return "needs_review", "not_visible_in_catalog"
    if row.expected_route_policy in CRITICAL_POLICIES and not place.is_route_eligible:
        return "needs_review", "not_route_eligible"
    return "matched", None


def _status_for_observation(observation: SourceObservation) -> tuple[str, str]:
    reason = observation.rejection_reason or "source_absent"
    if observation.raw_payload:
        tags = observation.raw_payload.get("tags") if isinstance(observation.raw_payload, dict) else None
        if isinstance(tags, dict):
            taxonomy_reason = unsupported_tag_reason(tags)
            if taxonomy_reason == "unsupported_tag":
                return "tag_unsupported", "unsupported_tag"
    return REJECTION_REASON_TO_GAP.get(reason, ("source_absent", "source_absent"))


def _row_needs_update(row: KnownMissingPoi, evaluated: dict[str, Any]) -> bool:
    return (
        row.status != evaluated["status"]
        or row.gap_reason != evaluated.get("gap_reason")
        or row.matched_place_id != evaluated.get("matched_place_id")
    )


def _summary_from_rows(rows: Iterable[KnownMissingPoi]) -> dict[str, Any]:
    row_list = list(rows)
    by_status = Counter(row.status for row in row_list)
    by_gap_reason = Counter(row.gap_reason or "none" for row in row_list)
    by_category = Counter(row.expected_category for row in row_list)
    critical_unresolved = sum(
        1 for row in row_list
        if row.expected_route_policy in CRITICAL_POLICIES and row.status not in MATCHED_STATUSES
    )
    return {
        "total": len(row_list),
        "matched": by_status.get("matched", 0),
        "unresolved": sum(1 for row in row_list if row.status in UNRESOLVED_STATUSES),
        "critical_unresolved": critical_unresolved,
        "by_status": dict(by_status),
        "by_gap_reason": dict(by_gap_reason),
        "by_expected_category": dict(by_category),
    }


def _row_to_api_item(row: KnownMissingPoi) -> dict[str, Any]:
    city = row.city
    place = row.matched_place
    return {
        "id": row.id,
        "city_slug": city.slug if city else None,
        "city_name": city.name if city else None,
        "slug": row.slug,
        "name": row.name_ru or row.name_en or row.name_local or row.slug,
        "name_local": row.name_local,
        "name_en": row.name_en,
        "name_ru": row.name_ru,
        "lat": row.lat,
        "lng": row.lng,
        "coordinate_precision": row.coordinate_precision,
        "expected_category": row.expected_category,
        "expected_scope": row.expected_scope,
        "expected_route_policy": row.expected_route_policy,
        "significance": row.significance,
        "source": row.source,
        "external_refs": row.external_refs or [],
        "status": row.status,
        "gap_reason": row.gap_reason,
        "review_notes": row.review_notes,
        "matched_place_id": row.matched_place_id,
        "matched_place_title": place.title if place else None,
        "matched_place_slug": place.slug if place else None,
        "matched_place_visible": bool(place.is_visible_in_catalog) if place else None,
        "matched_place_route_eligible": bool(place.is_route_eligible) if place else None,
        "last_checked_at": row.last_checked_at.isoformat() if row.last_checked_at else None,
        "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
    }


def _row_as_seed(row: KnownMissingPoi) -> dict[str, Any]:
    return {"city_slug": row.city.slug if row.city else None, "lat": row.lat, "lng": row.lng}


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


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _max_match_distance_m(category: str) -> float:
    return {
        "food": 140.0,
        "cafe": 140.0,
        "park": 220.0,
        "culture": 360.0,
        "walk": 500.0,
    }.get(category, 220.0)


def _category_matches(expected_category: str, actual_category: str | None) -> bool:
    if not actual_category:
        return False
    return actual_category in CATEGORY_COMPATIBILITY.get(expected_category, {expected_category})


def _candidate_names(row: KnownMissingPoi) -> list[str]:
    return [name for name in (row.name_local, row.name_en, row.name_ru, row.slug.replace("-", " ")) if name]


def _best_name_score(expected_names: Iterable[str], actual_names: Iterable[str | None]) -> float:
    best = 0.0
    for expected in expected_names:
        normalized_expected = _normalize_text(expected)
        if not normalized_expected:
            continue
        for actual in actual_names:
            normalized_actual = _normalize_text(actual or "")
            if not normalized_actual:
                continue
            if normalized_expected in normalized_actual or normalized_actual in normalized_expected:
                best = max(best, 0.92)
            best = max(best, SequenceMatcher(None, normalized_expected, normalized_actual).ratio())
    return best


def _normalize_text(value: str) -> str:
    return re.sub(r"[^a-zа-яё0-9]+", " ", value.lower(), flags=re.IGNORECASE).strip()


def _place_matches_external_ref(place: Place, external_refs: list[dict[str, str]]) -> bool:
    if not place.source_url:
        return False
    return any(ref.get("url") == place.source_url for ref in external_refs if isinstance(ref, dict))


def _review_note(status: str, reason: str | None, meta: dict[str, Any]) -> str:
    if status == "matched":
        return f"Matched automatically: distance={meta.get('distance_m')}m, name_score={meta.get('name_score')}."
    return f"Matched but requires review: reason={reason}, distance={meta.get('distance_m')}m, name_score={meta.get('name_score')}."
