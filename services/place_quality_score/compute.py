"""Place Quality Score (0–100), без AI."""

from __future__ import annotations

from models.place import Place

LOW_QUALITY_THRESHOLD = 50


def compute_place_quality_score(place: Place) -> int:
    score = 0
    if _has_coordinates(place):
        score += 15
    if place.image_url:
        score += 20
    if place.address and str(place.address).strip():
        score += 20
    if place.short_description and str(place.short_description).strip():
        score += 15
    if place.opening_hours:
        score += 15
    if place.source_url and str(place.source_url).strip():
        score += 5
    if place.verification_status == "verified":
        score += 10
    return min(score, 100)


def quality_bucket(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= LOW_QUALITY_THRESHOLD:
        return "medium"
    return "low"


def is_low_quality(score: int) -> bool:
    return score < LOW_QUALITY_THRESHOLD


def _has_coordinates(place: Place) -> bool:
    if place.lat is None or place.lng is None:
        return False
    return not (place.lat == 0.0 and place.lng == 0.0)
