"""Предупреждения маршрута, связанные с адресами точек."""

from __future__ import annotations

from services.place_address_policy import is_unclear_for_display


def missing_address_text() -> str:
    return "В маршруте есть точки без точного адреса — откройте их на карте."


def missing_address_warning_items(points: object) -> list[dict[str, object]]:
    affected = _affected_place_ids(points)
    if not affected:
        return []
    return [{
        "type": "missing_address",
        "severity": "info",
        "user_message": missing_address_text(),
        "affected_place_ids": affected,
        "action_hint": "Используйте ссылки Google/Яндекс/OSM для навигации.",
    }]


def route_warnings_with_missing_address(existing: list[str], points: object) -> list[str]:
    if not _affected_place_ids(points):
        return list(existing)
    text = missing_address_text()
    return list(existing) if text in existing else [*list(existing), text]


def _affected_place_ids(points: object) -> list[str]:
    items = list(points) if points is not None else []
    return [
        str(getattr(point, "place_id", ""))
        for point in items
        if is_unclear_for_display(getattr(point, "address", None), getattr(point, "category", None))
        and str(getattr(point, "place_id", "")).strip()
    ]
