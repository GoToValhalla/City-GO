"""Оценка: может ли place участвовать в маршруте."""

from __future__ import annotations

from dataclasses import dataclass

from models.city import City
from models.place import Place
from services.data_foundation_policy import ROUTE_ALLOWED_QUALITY_TIERS
from services.place_quality_signals import is_placeholder_title
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


@dataclass(frozen=True)
class RouteEligibilityResult:
    eligible: bool
    reasons: tuple[str, ...]


def _canonical_category(place: Place) -> str:
    """Возвращает каноническую категорию с legacy fallback.

    P0 добавляет `canonical_category`, но существующие места ещё могут иметь только `category`.
    Fallback нужен, чтобы не обнулить маршруты до полной миграции данных.
    """
    return (getattr(place, "canonical_category", None) or place.category or "").strip().lower()


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

    lifecycle_status = getattr(place, "lifecycle_status", None) or "active"
    if lifecycle_status != "active":
        reasons.append("lifecycle_not_active")

    if not getattr(place, "is_published", True):
        reasons.append("place_not_published")
    if not getattr(place, "is_visible_in_catalog", True):
        reasons.append("place_not_visible_in_catalog")
    if not getattr(place, "is_route_eligible", True):
        reasons.append("route_eligible_false")
    if is_placeholder_title(getattr(place, "title", None)):
        reasons.append("placeholder_title")
    if place.lat is None or place.lng is None:
        reasons.append("missing_coordinates")
    elif place.lat == 0.0 and place.lng == 0.0:
        reasons.append("invalid_coordinates")

    category = _canonical_category(place)
    if not category:
        reasons.append("missing_canonical_category")
    elif category in ROUTE_FORBIDDEN_CATEGORIES:
        reasons.append(f"forbidden_category:{category}")

    quality_tier = (getattr(place, "quality_tier", None) or "silver").strip().lower()
    if quality_tier not in ROUTE_ALLOWED_QUALITY_TIERS:
        reasons.append(f"quality_tier_not_route_allowed:{quality_tier or 'empty'}")

    if getattr(place, "is_spam_poi", False):
        reasons.append("spam_poi")
    if getattr(place, "is_duplicate_suspected", False):
        reasons.append("duplicate_suspected")
    if getattr(place, "critical_field_expired", False):
        reasons.append("critical_field_expired")
    if getattr(place, "publication_status", "published") == "archived":
        reasons.append("place_archived")

    return RouteEligibilityResult(eligible=not reasons, reasons=tuple(reasons))