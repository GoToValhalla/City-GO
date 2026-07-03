from __future__ import annotations

import re
from typing import Any

from models.place import Place
from services.route_eligibility_policy import (
    HARD_EXCLUDED_CATEGORIES,
    canonical_category_for_place,
    evaluate_place_route_eligibility,
)

NON_TOURIST_CATEGORIES = {
    "service", "services", "bank", "atm", "mvd", "police", "government",
    "transport", "stop", "bus_stop", "bus_station", "railway_station",
    "hospital", "health", "medical", "pharmacy", "military", "cemetery",
    "industrial", "waste_disposal", "fuel", "parking", "car_service",
}
NON_TOURIST_CATEGORIES = NON_TOURIST_CATEGORIES | HARD_EXCLUDED_CATEGORIES
PUBLICATION_STATUSES = {"published", "auto_published", "limited_published"}
_TECHNICAL_TITLE_PATTERNS = (
    re.compile(r"^(node|way|relation)[/:\s-]*\d+$", re.IGNORECASE),
    re.compile(r"^osm[/:\s-]*\d+$", re.IGNORECASE),
    re.compile(r"^.+\s+osm\s+\d+$", re.IGNORECASE),
    re.compile(r"^\d+$"),
)


def category_code(place: Place | Any) -> str | None:
    return canonical_category_for_place(place)


def is_non_tourist_category(category: str | None) -> bool:
    return (category or "").strip().lower() in NON_TOURIST_CATEGORIES


def is_technical_osm_title(title: str | None) -> bool:
    value = (title or "").strip()
    return any(pattern.match(value) for pattern in _TECHNICAL_TITLE_PATTERNS)


def is_public_place_visible(place: Place) -> bool:
    category = category_code(place)
    return (
        bool(place.is_active)
        and getattr(place, "status", None) in {None, "active"}
        and bool(place.is_published)
        and bool(place.is_visible_in_catalog)
        and getattr(place, "publication_status", None) in PUBLICATION_STATUSES
        and not bool(getattr(place, "is_spam_poi", False))
        and not is_non_tourist_category(category)
        and not is_technical_osm_title(place.title)
    )


def is_public_route_place_eligible(place: Place) -> bool:
    return evaluate_place_route_eligibility(place, require_stored_flag=True).eligible
