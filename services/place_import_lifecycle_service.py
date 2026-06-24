from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from typing import Any

from models.place import Place

ACTIVE_STATUS = "active"
DRAFT_STATUS = "draft"
NEEDS_REVIEW_STATUS = "needs_review"
CLOSED_STATUS = "closed"
TEMPORARILY_CLOSED_STATUS = "temporarily_closed"
REMOVED_FROM_SOURCE_STATUS = "removed_from_source"

MAX_AUTOMATIC_COORDINATE_DRIFT_METERS = 350

BAD_EXISTING_TITLE_VALUES = {
    "yes", "no", "none", "null", "unknown", "fixme", "todo", "n/a", "na",
}

CATEGORY_GROUPS = {
    "food": {"cafe", "food"},
    "culture": {"museum", "culture", "viewpoint"},
    "nature": {"walk", "park", "beach", "viewpoint"},
    "useful": {"useful", "health"},
}


@dataclass
class PlaceImportDecision:
    action: str
    status: str
    is_active: bool
    changed_fields: list[str]
    review_reasons: list[str]


def apply_accepted_import_to_place(
    place: Place,
    item: dict[str, Any],
    category_id: int,
    visit_duration_minutes: int,
) -> PlaceImportDecision:
    """Apply only a real source diff and require review for every changed place."""
    incoming_title = str(item["title"])
    incoming_category = str(item["category"])
    incoming_lat = float(item["raw_lat"])
    incoming_lng = float(item["raw_lng"])
    incoming_lifecycle_status = str(item.get("lifecycle_status") or ACTIVE_STATUS)

    if _is_bad_title(incoming_title):
        return hide_place(place=place, reason="bad_import_title", status=DRAFT_STATUS)
    if incoming_lifecycle_status == CLOSED_STATUS:
        return hide_place(place=place, reason="source_closed", status=CLOSED_STATUS)
    if incoming_lifecycle_status == TEMPORARILY_CLOSED_STATUS:
        return hide_place(place=place, reason="source_temporarily_closed", status=TEMPORARILY_CLOSED_STATUS)
    if incoming_lifecycle_status == REMOVED_FROM_SOURCE_STATUS:
        return hide_place(place=place, reason="source_removed", status=REMOVED_FROM_SOURCE_STATUS)

    proposed: dict[str, Any] = {
        "category_id": category_id,
        "title": incoming_title,
        "short_description": item.get("short_description"),
        "category": incoming_category,
        "address": item.get("address"),
        "lat": incoming_lat,
        "lng": incoming_lng,
        "source": "osm",
        "source_url": item.get("source_url"),
    }
    if item.get("opening_hours"):
        proposed["opening_hours"] = item["opening_hours"]
    if item.get("website"):
        proposed["website"] = item["website"]
    if item.get("phone"):
        proposed["phone"] = item["phone"]
    if place.average_visit_duration_minutes is None:
        proposed["average_visit_duration_minutes"] = visit_duration_minutes

    changed_fields = [field for field, value in proposed.items() if getattr(place, field) != value]
    if not changed_fields:
        return PlaceImportDecision(
            action="unchanged",
            status=place.status,
            is_active=bool(place.is_active),
            changed_fields=[],
            review_reasons=[],
        )

    review_reasons = ["source_data_changed"]
    coordinate_drift_meters = _coordinate_drift_meters(
        old_lat=place.lat,
        old_lng=place.lng,
        new_lat=incoming_lat,
        new_lng=incoming_lng,
    )
    if coordinate_drift_meters is not None and coordinate_drift_meters > MAX_AUTOMATIC_COORDINATE_DRIFT_METERS:
        review_reasons.append("large_coordinate_drift")
    if _is_major_category_change(place.category, incoming_category):
        review_reasons.append("major_category_change")

    for field, value in proposed.items():
        _set_if_changed(place, field, value, changed_fields=None)

    _mark_place_for_review(place, changed_fields)
    return PlaceImportDecision(
        action="needs_review",
        status=NEEDS_REVIEW_STATUS,
        is_active=False,
        changed_fields=changed_fields,
        review_reasons=review_reasons,
    )


def mark_place_for_review(place: Place, *, reason: str = "enrichment_changed") -> PlaceImportDecision:
    """Move an enriched place out of public surfaces until an admin confirms it."""
    changed_fields: list[str] = []
    _mark_place_for_review(place, changed_fields)
    return PlaceImportDecision(
        action="needs_review",
        status=NEEDS_REVIEW_STATUS,
        is_active=False,
        changed_fields=changed_fields,
        review_reasons=[reason],
    )


def _mark_place_for_review(place: Place, changed_fields: list[str]) -> None:
    now = datetime.utcnow()
    was_public = bool(place.is_published or place.is_visible_in_catalog or place.is_searchable)
    _set_if_changed(place, "status", NEEDS_REVIEW_STATUS, changed_fields)
    _set_if_changed(place, "is_active", False, changed_fields)
    _set_if_changed(place, "is_published", False, changed_fields)
    _set_if_changed(place, "is_visible_in_catalog", False, changed_fields)
    _set_if_changed(place, "is_route_eligible", False, changed_fields)
    _set_if_changed(place, "is_searchable", False, changed_fields)
    _set_if_changed(place, "publication_status", NEEDS_REVIEW_STATUS, changed_fields)
    if was_public:
        _set_if_changed(place, "unpublished_at", now, changed_fields)
    _set_if_changed(place, "last_verified_at", now, changed_fields)
    _set_if_changed(place, "updated_at", now, changed_fields)


def hide_place(place: Place, reason: str, status: str = DRAFT_STATUS) -> PlaceImportDecision:
    """Hide a place without deleting it. A no-op remains a true no-op."""
    changed_fields: list[str] = []
    now = datetime.utcnow()
    was_public = bool(place.is_published or place.is_visible_in_catalog or place.is_searchable)
    _set_if_changed(place, "status", status, changed_fields)
    _set_if_changed(place, "is_active", False, changed_fields)
    _set_if_changed(place, "is_published", False, changed_fields)
    _set_if_changed(place, "is_visible_in_catalog", False, changed_fields)
    _set_if_changed(place, "is_route_eligible", False, changed_fields)
    _set_if_changed(place, "is_searchable", False, changed_fields)
    _set_if_changed(place, "publication_status", status, changed_fields)
    if was_public:
        _set_if_changed(place, "unpublished_at", now, changed_fields)
    if changed_fields:
        _set_if_changed(place, "last_verified_at", now, changed_fields)
        _set_if_changed(place, "updated_at", now, changed_fields)
    return PlaceImportDecision(
        action="hidden" if changed_fields else "unchanged",
        status=status,
        is_active=False,
        changed_fields=changed_fields,
        review_reasons=[reason] if changed_fields else [],
    )


def existing_place_must_be_hidden(place: Place) -> bool:
    if place.category == "transport" or _is_bad_title(place.title):
        return True
    return place.status in {
        CLOSED_STATUS,
        TEMPORARILY_CLOSED_STATUS,
        REMOVED_FROM_SOURCE_STATUS,
    }


def mark_missing_place(place: Place, missing_count: int) -> PlaceImportDecision:
    if missing_count < 3:
        return PlaceImportDecision(
            action="missing_tracked",
            status=place.status,
            is_active=bool(place.is_active),
            changed_fields=[],
            review_reasons=["missing_from_source"],
        )
    return hide_place(place=place, reason="missing_from_source_repeatedly", status=REMOVED_FROM_SOURCE_STATUS)


def _set_if_changed(
    place: Place,
    field_name: str,
    new_value: Any,
    changed_fields: list[str] | None,
) -> None:
    if getattr(place, field_name) == new_value:
        return
    setattr(place, field_name, new_value)
    if changed_fields is not None and field_name not in changed_fields:
        changed_fields.append(field_name)


def _is_bad_title(value: str | None) -> bool:
    if value is None:
        return True
    normalized = str(value).lower().strip()
    compact = "".join(normalized.split())
    if not compact or compact in BAD_EXISTING_TITLE_VALUES:
        return True
    numeric_candidate = normalized
    for char in ["№", "#", " ", ",", ".", ";", ":", "|", "/", "\\", "-", "–", "—", "_", "(", ")", "+"]:
        numeric_candidate = numeric_candidate.replace(char, "")
    return numeric_candidate.isdigit()


def _is_major_category_change(old_category: str | None, new_category: str | None) -> bool:
    if not old_category or not new_category or old_category == new_category:
        return False
    old_group = _category_group(old_category)
    new_group = _category_group(new_category)
    if old_group is None or new_group is None:
        return True
    return old_group != new_group


def _category_group(category: str) -> str | None:
    for group_name, group_categories in CATEGORY_GROUPS.items():
        if category in group_categories:
            return group_name
    return None


def _coordinate_drift_meters(
    old_lat: float | None,
    old_lng: float | None,
    new_lat: float | None,
    new_lng: float | None,
) -> float | None:
    if old_lat is None or old_lng is None or new_lat is None or new_lng is None:
        return None
    return _haversine_distance_meters(float(old_lat), float(old_lng), float(new_lat), float(new_lng))


def _haversine_distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_meters = 6371000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_meters * c
