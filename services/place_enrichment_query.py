"""Query logic: find places eligible for enrichment based on missing-field filters."""
from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place

# Predicate: returns True if the field is considered "missing" for this place.
_MISSING_CHECKS: dict[str, Callable[[Place], bool]] = {
    "address": lambda p: not (getattr(p, "address", None) or "").strip(),
    "photo": lambda p: not getattr(p, "image_url", None),
    "description": lambda p: not getattr(p, "short_description", None),
    "opening_hours": lambda p: not getattr(p, "opening_hours", None),
    "price_level": lambda p: getattr(p, "price_level", None) is None,
    "dog_friendly": lambda p: not getattr(p, "dog_friendly", False),
    "family_friendly": lambda p: not getattr(p, "family_friendly", False),
    "outdoor": lambda p: not getattr(p, "outdoor", False),
    "indoor": lambda p: not getattr(p, "indoor", False),
    # Not stored in Place model yet — always counts as missing
    "website": lambda _: True,
    "phone": lambda _: True,
    "menu_url": lambda _: True,
    "social_links": lambda _: True,
}


def query_places_for_enrichment(
    db: Session,
    *,
    city_slug: str,
    limit: int,
    only_published: bool,
    only_route_eligible: bool,
    missing_fields: list[str],
) -> list[Place]:
    q = db.query(Place).join(City).filter(City.slug == city_slug)
    if only_published:
        q = q.filter(Place.is_published.is_(True))
    if only_route_eligible:
        q = q.filter(Place.is_route_eligible.is_(True))

    candidates = q.limit(limit * 5).all()

    if not missing_fields:
        return candidates[:limit]

    filtered = [
        p for p in candidates
        if any(_MISSING_CHECKS.get(f, lambda _: True)(p) for f in missing_fields)
    ]
    return filtered[:limit]


def missing_fields_breakdown(places: list[Place], fields: list[str]) -> dict[str, int]:
    """Count how many places are missing each requested field."""
    return {
        f: sum(1 for p in places if _MISSING_CHECKS.get(f, lambda _: True)(p))
        for f in fields
    }
