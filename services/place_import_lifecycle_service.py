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
    """
    Обновляет существующее место по свежему OSM-снимку.

    Автоматически обновляем безопасные изменения:
    - название;
    - описание;
    - адрес;
    - часы работы;
    - координаты при небольшом смещении;
    - категорию внутри безопасной группы.

    Отправляем в needs_review:
    - резкий перенос координат;
    - резкую смену категории;
    - подозрительный lifecycle-статус источника.

    Закрываем/скрываем:
    - source_closed;
    - source_removed;
    - мусорные названия.
    """
    changed_fields: list[str] = []
    review_reasons: list[str] = []

    now = datetime.utcnow()

    incoming_title = str(item["title"])
    incoming_category = str(item["category"])
    incoming_lat = float(item["raw_lat"])
    incoming_lng = float(item["raw_lng"])
    incoming_lifecycle_status = str(item.get("lifecycle_status") or "active")

    if _is_bad_title(incoming_title):
        return hide_place(
            place=place,
            reason="bad_import_title",
            status=DRAFT_STATUS,
        )

    if incoming_lifecycle_status == "closed":
        return hide_place(
            place=place,
            reason="source_closed",
            status=CLOSED_STATUS,
        )

    if incoming_lifecycle_status == "temporarily_closed":
        return hide_place(
            place=place,
            reason="source_temporarily_closed",
            status=TEMPORARILY_CLOSED_STATUS,
        )

    if incoming_lifecycle_status == "removed_from_source":
        return hide_place(
            place=place,
            reason="source_removed",
            status=REMOVED_FROM_SOURCE_STATUS,
        )

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

    if review_reasons:
        _update_safe_text_fields(place, item, changed_fields)
        _set_if_changed(place, "source", "osm", changed_fields)
        _set_if_changed(place, "source_url", item["source_url"], changed_fields)
        _set_if_changed(place, "confidence", max(place.confidence or 0.0, 0.7), changed_fields)
        _set_if_changed(place, "last_verified_at", now, changed_fields)
        _set_if_changed(place, "status", NEEDS_REVIEW_STATUS, changed_fields)
        _set_if_changed(place, "is_active", False, changed_fields)
        _set_if_changed(place, "updated_at", now, changed_fields)

        return PlaceImportDecision(
            action="needs_review",
            status=NEEDS_REVIEW_STATUS,
            is_active=False,
            changed_fields=changed_fields,
            review_reasons=review_reasons,
        )

    _set_if_changed(place, "category_id", category_id, changed_fields)
    _set_if_changed(place, "title", incoming_title, changed_fields)
    _set_if_changed(place, "short_description", item["short_description"], changed_fields)
    _set_if_changed(place, "category", incoming_category, changed_fields)
    _set_if_changed(place, "address", item["address"], changed_fields)
    _set_if_changed(place, "lat", incoming_lat, changed_fields)
    _set_if_changed(place, "lng", incoming_lng, changed_fields)
    _set_if_changed(place, "source", "osm", changed_fields)
    _set_if_changed(place, "source_url", item["source_url"], changed_fields)
    _set_if_changed(place, "confidence", max(place.confidence or 0.0, 0.7), changed_fields)
    _set_if_changed(place, "status", ACTIVE_STATUS, changed_fields)
    _set_if_changed(place, "is_active", True, changed_fields)
    _set_if_changed(place, "last_verified_at", now, changed_fields)

    if item.get("opening_hours"):
        _set_if_changed(place, "opening_hours", item["opening_hours"], changed_fields)

    if place.average_visit_duration_minutes is None:
        _set_if_changed(
            place,
            "average_visit_duration_minutes",
            visit_duration_minutes,
            changed_fields,
        )

    _set_if_changed(place, "updated_at", now, changed_fields)

    return PlaceImportDecision(
        action="updated" if changed_fields else "unchanged",
        status=ACTIVE_STATUS,
        is_active=True,
        changed_fields=changed_fields,
        review_reasons=[],
    )


def hide_place(
    place: Place,
    reason: str,
    status: str = DRAFT_STATUS,
) -> PlaceImportDecision:
    """
    Скрывает место из публичного каталога, но не удаляет его из БД.
    """
    changed_fields: list[str] = []
    now = datetime.utcnow()

    _set_if_changed(place, "status", status, changed_fields)
    _set_if_changed(place, "is_active", False, changed_fields)
    _set_if_changed(place, "last_verified_at", now, changed_fields)
    _set_if_changed(place, "updated_at", now, changed_fields)

    return PlaceImportDecision(
        action="hidden",
        status=status,
        is_active=False,
        changed_fields=changed_fields,
        review_reasons=[reason],
    )


def existing_place_must_be_hidden(place: Place) -> bool:
    """
    Проверяет старые места, которые уже лежат в БД и должны быть скрыты:
    - транспорт;
    - мусорные названия;
    - неактуальные статусы.
    """
    if place.category == "transport":
        return True

    if _is_bad_title(place.title):
        return True

    if place.status in {
        CLOSED_STATUS,
        TEMPORARILY_CLOSED_STATUS,
        REMOVED_FROM_SOURCE_STATUS,
        NEEDS_REVIEW_STATUS,
    }:
        return True

    return False


def mark_missing_place(place: Place, missing_count: int) -> PlaceImportDecision:
    """
    Обрабатывает место, которое раньше было в источнике, но сейчас не найдено.

    1 пропуск — не скрываем.
    2 пропуска — не скрываем.
    3+ пропуска — скрываем как removed_from_source.
    """
    if missing_count < 3:
        return PlaceImportDecision(
            action="missing_tracked",
            status=place.status,
            is_active=bool(place.is_active),
            changed_fields=[],
            review_reasons=["missing_from_source"],
        )

    return hide_place(
        place=place,
        reason="missing_from_source_repeatedly",
        status=REMOVED_FROM_SOURCE_STATUS,
    )


def _update_safe_text_fields(
    place: Place,
    item: dict[str, Any],
    changed_fields: list[str],
) -> None:
    _set_if_changed(place, "title", item["title"], changed_fields)
    _set_if_changed(place, "short_description", item["short_description"], changed_fields)
    _set_if_changed(place, "address", item["address"], changed_fields)

    if item.get("opening_hours"):
        _set_if_changed(place, "opening_hours", item["opening_hours"], changed_fields)


def _set_if_changed(
    place: Place,
    field_name: str,
    new_value: Any,
    changed_fields: list[str],
) -> None:
    old_value = getattr(place, field_name)

    if old_value != new_value:
        setattr(place, field_name, new_value)
        changed_fields.append(field_name)


def _is_bad_title(value: str | None) -> bool:
    if value is None:
        return True

    normalized = str(value).lower().strip()
    compact = "".join(normalized.split())

    if not compact:
        return True

    if compact in BAD_EXISTING_TITLE_VALUES:
        return True

    numeric_candidate = normalized
    for char in ["№", "#", " ", ",", ".", ";", ":", "|", "/", "\\", "-", "–", "—", "_", "(", ")", "+"]:
        numeric_candidate = numeric_candidate.replace(char, "")

    if numeric_candidate.isdigit():
        return True

    return False


def _is_major_category_change(
    old_category: str | None,
    new_category: str | None,
) -> bool:
    if not old_category or not new_category:
        return False

    if old_category == new_category:
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

    return _haversine_distance_meters(
        lat1=float(old_lat),
        lng1=float(old_lng),
        lat2=float(new_lat),
        lng2=float(new_lng),
    )


def _haversine_distance_meters(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    earth_radius_meters = 6371000.0

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_meters * c
