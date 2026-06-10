"""
Аннотация качества данных Place для recommendation pipeline.

Только диагностика: места не отфильтровываются и не меняют скоринг.
Результат вешается на объект места как place.validation = validate_place(place).
"""

from __future__ import annotations

from typing import Any

from services.itinerary_time_service import parse_time_string

_ALLOWED_OPENING_KEYS = frozenset({"open", "close"})


def _issue_opening_hours(issues: list[str], code: str) -> None:
    """Добавляет код проблемы по часам, без дублей одного и того же кода подряд."""
    if not issues or issues[-1] != code:
        issues.append(code)


def _validate_opening_hours_structure(raw: Any, issues: list[str]) -> None:
    """
    None — допустимо (часы не заданы).
    dict — ожидаемые значения по дням: None или {"open": "HH:MM", "close": "HH:MM"}.
    Иной тип или несовместимая структура — только флаги в issues.
    """
    if raw is None:
        return

    if not isinstance(raw, dict):
        _issue_opening_hours(issues, "opening_hours_invalid_type")
        return

    for _day_key, day_info in raw.items():
        if day_info is None:
            continue
        if not isinstance(day_info, dict):
            _issue_opening_hours(issues, "opening_hours_day_invalid")
            continue

        for k in day_info:
            if k not in _ALLOWED_OPENING_KEYS:
                _issue_opening_hours(issues, "opening_hours_unknown_key")
                break

        for time_key in ("open", "close"):
            if time_key not in day_info:
                continue
            val = day_info[time_key]
            if val is None:
                continue
            if not isinstance(val, str):
                _issue_opening_hours(issues, "opening_hours_time_not_string")
                break
            if val.strip() == "":
                _issue_opening_hours(issues, "opening_hours_empty_time_string")
                break
            if parse_time_string(val) is None:
                _issue_opening_hours(issues, "opening_hours_unparseable_time")
                break


def validate_place(place: Any) -> dict[str, Any]:
    """
    Проверяет базовые поля места (координаты, часы, длительность визита, категория, ценовой уровень).

    Возвращает словарь:
      is_valid — True, если issues пуст;
      issues — список строковых кодов проблем (для логов и отладки).
    """
    issues: list[str] = []

    lat = getattr(place, "lat", None)
    if lat is None:
        issues.append("lat_missing")
    elif isinstance(lat, bool):
        issues.append("lat_invalid_type")
    elif not isinstance(lat, (int, float)):
        issues.append("lat_invalid_type")
    else:
        lat_f = float(lat)
        if not (-90.0 <= lat_f <= 90.0):
            issues.append("lat_out_of_range")

    lng = getattr(place, "lng", None)
    if lng is None:
        issues.append("lng_missing")
    elif isinstance(lng, bool):
        issues.append("lng_invalid_type")
    elif not isinstance(lng, (int, float)):
        issues.append("lng_invalid_type")
    else:
        lng_f = float(lng)
        if not (-180.0 <= lng_f <= 180.0):
            issues.append("lng_out_of_range")

    _validate_opening_hours_structure(getattr(place, "opening_hours", None), issues)

    duration = getattr(place, "average_visit_duration_minutes", None)
    if duration is not None:
        if isinstance(duration, bool) or not isinstance(duration, int):
            issues.append("visit_duration_invalid_type")
        elif duration <= 0:
            issues.append("visit_duration_non_positive")

    category = getattr(place, "category", None)
    if category == "":
        issues.append("category_empty")

    price_level = getattr(place, "price_level", None)
    if price_level is not None:
        if isinstance(price_level, bool) or not isinstance(price_level, int):
            issues.append("price_level_invalid_type")
        elif price_level < 0 or price_level > 3:
            issues.append("price_level_out_of_range")

    return {
        "is_valid": len(issues) == 0,
        "issues": issues,
    }
