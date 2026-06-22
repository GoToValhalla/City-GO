from __future__ import annotations

from models.place import Place
from services.route_geometry import distance_meters


def place_quality(place: Place, start_lat: float, start_lng: float) -> float:
    has_photo = 1.0 if getattr(place, "image_url", None) else 0.0
    has_description = 1.0 if getattr(place, "short_description", None) else 0.0
    has_address = 1.0 if getattr(place, "address", None) else 0.0
    confidence = _confidence(place)
    distance_score = _distance_score(place, start_lat, start_lng)
    return (
        0.30 * has_photo
        + 0.20 * has_description
        + 0.15 * has_address
        + 0.20 * confidence
        + 0.15 * distance_score
    )


def category_multiplier(place: Place, selected: list[str], mode: str) -> float:
    if mode != "balanced" or not selected:
        return 1.0
    return 2.5 if (place.category or "") in selected else 1.0


def weighted_score(place: Place, start_lat: float, start_lng: float, selected: list[str], mode: str) -> float:
    return place_quality(place, start_lat, start_lng) * category_multiplier(place, selected, mode)


def _confidence(place: Place) -> float:
    if place.confidence_score:
        return min(max(float(place.confidence_score) / 10.0, 0.0), 1.0)
    if place.confidence is not None:
        return min(max(float(place.confidence), 0.0), 1.0)
    return 0.5


def _distance_score(place: Place, start_lat: float, start_lng: float) -> float:
    meters = distance_meters(start_lat, start_lng, float(place.lat), float(place.lng))
    return max(0.0, 1.0 - min(meters, 5000.0) / 5000.0)
