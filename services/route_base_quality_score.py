from __future__ import annotations


def base_quality_score(place: object) -> float:
    parts = (
        0.3 if _has_coordinates(place) else 0.0,
        _opening_score(place) * 0.25,
        0.2 if _has_visit_duration(place) else 0.0,
        _image_score(place) * 0.15,
        0.1 if _has_text(getattr(place, "short_description", None)) else 0.0,
    )
    return max(0.0, min(1.0, sum(parts)))


def _opening_score(place: object) -> float:
    hours = getattr(place, "opening_hours", None)
    return 1.0 if isinstance(hours, dict) and bool(hours) else 0.35


def _image_score(place: object) -> float:
    image = getattr(place, "image", None)
    if isinstance(image, dict):
        return 1.0 if image.get("match_status") == "exact_place_photo" else 0.55
    return 0.8 if _has_text(getattr(place, "image_url", None)) else 0.0


def _has_coordinates(place: object) -> bool:
    return _is_number(getattr(place, "lat", None)) and _is_number(getattr(place, "lng", None))


def _has_visit_duration(place: object) -> bool:
    value = getattr(place, "average_visit_duration_minutes", None)
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _has_text(value: object) -> bool:
    return bool(str(value or "").strip())
