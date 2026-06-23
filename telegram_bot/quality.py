from __future__ import annotations

import re
from typing import Any

from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence

NON_TOURIST_CATEGORIES = {
    "service",
    "bank",
    "atm",
    "mvd",
    "police",
    "government",
    "transport",
    "hospital",
    "health",
    "medical",
    "pharmacy",
    "military",
    "cemetery",
    "industrial",
    "waste_disposal",
    "fuel",
    "parking",
    "car_service",
}

_TECHNICAL_TITLE_PATTERNS = (
    re.compile(r"^(node|way|relation)[/:\s-]*\d+$", re.IGNORECASE),
    re.compile(r"^osm[/:\s-]*\d+$", re.IGNORECASE),
    re.compile(r"^место\s+osm\s+\d+$", re.IGNORECASE),
    re.compile(r"^культурное\s+место\s+osm\s+\d+$", re.IGNORECASE),
    re.compile(r"^место\s+для\s+прогулки\s+osm\s+\d+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
)

PUBLICATION_STATUSES = {"published", "auto_published", "limited_published"}


def clean_title(title: str | None) -> str:
    value = (title or "").strip()
    if not value or is_technical_osm_title(value):
        return "Без названия"
    return value


def is_technical_osm_title(title: str | None) -> bool:
    value = (title or "").strip()
    return any(pattern.match(value) for pattern in _TECHNICAL_TITLE_PATTERNS)


def category_code(place: Place | Any) -> str | None:
    return getattr(place, "canonical_category", None) or getattr(place, "category", None)


def is_non_tourist_category(category: str | None) -> bool:
    return bool(category and category in NON_TOURIST_CATEGORIES)


def is_place_bot_visible(place: Place) -> bool:
    category = category_code(place)
    return (
        bool(place.is_active)
        and place.status in {None, "active"}
        and bool(place.is_published)
        and bool(place.is_visible_in_catalog)
        and place.publication_status in PUBLICATION_STATUSES
        and not bool(place.is_spam_poi)
        and not is_non_tourist_category(category)
        and not is_technical_osm_title(place.title)
    )


def is_route_point_bot_eligible(place: Place) -> bool:
    return is_place_bot_visible(place) and bool(place.is_route_eligible) and place.lat is not None and place.lng is not None


def is_hours_reliable(confidence: PlaceFieldConfidence | None) -> bool:
    if confidence is None:
        return False
    return (
        confidence.confidence_level in {"high", "medium"}
        and confidence.freshness_status != "stale"
        and confidence.conflict_status in {None, "none"}
    )
