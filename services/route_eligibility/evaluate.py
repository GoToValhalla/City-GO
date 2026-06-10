"""Оценка: может ли place участвовать в маршруте."""

from __future__ import annotations

from dataclasses import dataclass

from models.city import City
from models.place import Place

from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


@dataclass(frozen=True)
class RouteEligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]


def evaluate_place_route_eligibility(
    place: Place,
    *,
    city: City | None = None,
) -> RouteEligibilityResult:
    reasons: list[str] = []
    if not place.city_id:
        reasons.append("missing_city_id")
    if city is not None:
        if getattr(city, "is_active", True) is False:
            reasons.append("city_inactive")
        if getattr(city, "launch_status", "published") != "published":
            reasons.append("city_not_published")
    if not getattr(place, "is_active", True):
        reasons.append("place_inactive")
    if getattr(place, "status", "active") != "active":
        reasons.append("place_status_not_active")
    if not getattr(place, "is_published", True):
        reasons.append("place_not_published")
    if not getattr(place, "is_visible_in_catalog", True):
        reasons.append("place_not_visible_in_catalog")
    if not getattr(place, "is_route_eligible", True):
        reasons.append("route_eligible_false")
    if place.lat is None or place.lng is None:
        reasons.append("missing_coordinates")
    elif place.lat == 0.0 and place.lng == 0.0:
        reasons.append("invalid_coordinates")
    category = (place.category or "").strip().lower()
    if category and category in ROUTE_FORBIDDEN_CATEGORIES:
        reasons.append(f"forbidden_category:{category}")
    return RouteEligibilityResult(eligible=not reasons, reasons=tuple(reasons))
