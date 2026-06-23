from __future__ import annotations

from models.place_field_confidence import PlaceFieldConfidence
from services.public_place_quality import (
    NON_TOURIST_CATEGORIES,
    PUBLICATION_STATUSES,
    category_code,
    is_non_tourist_category,
    is_public_place_visible,
    is_public_route_place_eligible,
    is_technical_osm_title,
)


def clean_title(title: str | None) -> str:
    value = (title or "").strip()
    if not value or is_technical_osm_title(value):
        return "Без названия"
    return value


def is_place_bot_visible(place) -> bool:
    return is_public_place_visible(place)


def is_route_point_bot_eligible(place) -> bool:
    return is_public_route_place_eligible(place)


def is_hours_reliable(confidence: PlaceFieldConfidence | None) -> bool:
    if confidence is None:
        return False
    return (
        confidence.confidence_level in {"high", "medium"}
        and confidence.freshness_status != "stale"
        and confidence.conflict_status in {None, "none"}
    )


__all__ = [
    "NON_TOURIST_CATEGORIES",
    "PUBLICATION_STATUSES",
    "category_code",
    "clean_title",
    "is_hours_reliable",
    "is_non_tourist_category",
    "is_place_bot_visible",
    "is_route_point_bot_eligible",
    "is_technical_osm_title",
]
