from __future__ import annotations

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

ALIASES = {
    "cafe": "coffee", "coffee_shop": "coffee", "fast_food": "food",
    "restaurant": "food", "bar": "evening", "pub": "evening",
    "museum": "culture", "gallery": "culture", "attraction": "culture",
    "viewpoint": "walk", "beach": "walk", "garden": "park",
}

DURATIONS = {
    "coffee": 20, "food": 45, "walk": 25, "park": 35, "culture": 45,
    "evening": 60, "family": 45, "dog-friendly": 25, "indoor": 30,
    "outdoor": 25, "service": 15,
}

HOURS = {
    "coffee": ("08:00", "21:00"), "food": ("11:00", "22:00"),
    "walk": ("00:00", "23:59"), "park": ("00:00", "23:59"),
    "culture": ("10:00", "18:00"), "evening": ("17:00", "01:00"),
    "family": ("10:00", "20:00"), "dog-friendly": ("00:00", "23:59"),
    "indoor": ("10:00", "21:00"), "outdoor": ("00:00", "23:59"),
    "service": ("10:00", "19:00"),
}


def normalized_category(value: object) -> str:
    raw = str(value or "").strip().casefold()
    return ALIASES.get(raw, raw)


def effective_visit_duration(place: object) -> int:
    cached = _positive_int(getattr(place, "effective_visit_duration_minutes", None))
    if cached is not None:
        return cached
    raw = _positive_int(getattr(place, "average_visit_duration_minutes", None))
    if raw is not None:
        return _clamp_runtime_duration(raw, place)
    return DURATIONS.get(normalized_category(getattr(place, "category", "")), 30)


def effective_opening_hours(place: object) -> dict[str, dict[str, str]]:
    cached = _non_empty_dict(getattr(place, "effective_opening_hours", None))
    if cached is not None:
        return cached
    raw = _non_empty_dict(getattr(place, "opening_hours", None))
    if raw is not None:
        return raw
    open_time, close_time = _default_hours_pair(place)
    return dict(map(lambda day: (day, {"open": open_time, "close": close_time}), DAYS))


def apply_runtime_place_defaults(place: object) -> object:
    if not isinstance(getattr(place, "opening_hours", None), dict):
        setattr(place, "effective_opening_hours", effective_opening_hours(place))
        setattr(place, "opening_hours_mode", "estimated_default")
    if not getattr(place, "average_visit_duration_minutes", None):
        setattr(place, "effective_visit_duration_minutes", effective_visit_duration(place))
        setattr(place, "visit_duration_source", "category_default")
    return place


def _positive_int(value: object) -> int | None:
    valid = isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0
    return int(value) if valid else None


def _non_empty_dict(value: object) -> dict[str, dict[str, str]] | None:
    return value if isinstance(value, dict) and bool(value) else None


def _default_hours_pair(place: object) -> tuple[str, str]:
    category = normalized_category(getattr(place, "category", ""))
    fallback = HOURS["outdoor"] if bool(getattr(place, "outdoor", False)) else HOURS["indoor"]
    return HOURS.get(category, fallback)


def _clamp_runtime_duration(value: int, place: object) -> int:
    category = normalized_category(getattr(place, "category", ""))
    if category in {"walk", "park", "coffee", "dog-friendly", "outdoor"}:
        return min(value, 35)
    if category in {"culture", "family", "indoor"}:
        return min(value, 45)
    if category in {"food", "evening"}:
        return min(value, 60)
    return min(value, 40)
