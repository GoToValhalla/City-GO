from __future__ import annotations


MATRIX = {
    "coffee": {"morning": 1.0, "afternoon": 0.78, "evening": 0.45, "night": 0.2},
    "cafe": {"morning": 1.0, "afternoon": 0.78, "evening": 0.45, "night": 0.2},
    "food": {"morning": 0.55, "afternoon": 0.9, "evening": 1.0, "night": 0.35},
    "restaurant": {"morning": 0.55, "afternoon": 0.9, "evening": 1.0, "night": 0.35},
    "evening": {"morning": 0.15, "afternoon": 0.35, "evening": 1.0, "night": 0.85},
    "bar": {"morning": 0.15, "afternoon": 0.35, "evening": 1.0, "night": 0.85},
    "park": {"morning": 0.9, "afternoon": 0.78, "evening": 0.62, "night": 0.2},
    "walk": {"morning": 0.92, "afternoon": 0.78, "evening": 0.85, "night": 0.25},
    "culture": {"morning": 0.78, "afternoon": 1.0, "evening": 0.52, "night": 0.15},
    "museum": {"morning": 0.78, "afternoon": 1.0, "evening": 0.52, "night": 0.15},
}


def time_context_score(place: object, time_of_day: str | None) -> float:
    bucket = _norm(time_of_day)
    if not bucket:
        return 0.75
    values = [MATRIX.get(category, {}).get(bucket, 0.68) for category in _categories(place)]
    return max(values or [0.68])


def _categories(place: object) -> tuple[str, ...]:
    raw = str(getattr(place, "category", "") or "")
    return tuple(_norm(item) for item in raw.split(",") if _norm(item))


def _norm(value: object) -> str:
    return str(value or "").strip().casefold()
