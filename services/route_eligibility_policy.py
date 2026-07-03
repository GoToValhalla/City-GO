"""Single source of truth for tourist walking route eligibility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, not_, or_

from models.category import Category
from models.place import Place
from services.data_foundation_policy import ROUTE_ALLOWED_QUALITY_TIERS
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS, is_placeholder_title
from services.route_diversity_policy import normalize_category

ROUTE_ALLOWED_PLACE_LAYERS = ("tourist_catalog", "food_layer")
NON_WALKING_POLICIES = ("day_trip", "region_scope", "infra_only", "transfer_only", "not_for_routes", "never")
PUBLICATION_STATUSES = ("published", "auto_published", "limited_published")

HARD_EXCLUDED_CATEGORIES = frozenset(
    {
        "medical", "health", "healthcare", "hospital", "clinic", "pharmacy", "apteka",
        "bank", "atm", "parking", "fuel", "toilet", "toilets", "public_toilet",
        "police", "bus_stop", "stop", "transport", "public_transport", "service",
        "services", "utility", "industrial", "shelter", "post_office",
        "vending_machine", "bench", "waste_basket", "charging_station",
        "car_service", "mvd", "government", "military", "cemetery", "waste_disposal",
        "generic_service", "transport_stop", "tram_stop", "gas_station", "useful",
        "unknown", "other", "office", "hotel", "shopping", "shop", "supermarket",
        "shopping_mall", "mall",
    }
)

ALLOWED_ROUTE_CATEGORIES = frozenset(
    {
        "museum", "park", "viewpoint", "architecture", "beach", "embankment",
        "nature", "restaurant", "cafe", "bar", "theatre", "gallery", "landmark",
        "entertainment", "historical_site", "history", "culture", "walk", "food",
        "attraction", "family", "sport", "market", "coffee", "monument", "historic",
        "promenade", "sightseeing",
    }
)


@dataclass(frozen=True)
class RouteEligibilityVerdict:
    eligible: bool
    reasons: tuple[str, ...]
    canonical_category: str | None = None
    admin_bucket: str = "route_eligible"


def canonical_category_for_place(place: Any) -> str | None:
    raw = getattr(place, "canonical_category", None)
    if isinstance(raw, str) and raw.strip():
        return normalize_category(raw)
    category = getattr(place, "category_ref", None)
    code = getattr(category, "code", None)
    return normalize_category(code) if isinstance(code, str) and code.strip() else None


def evaluate_place_route_eligibility(
    place: Any,
    *,
    city: Any | None = None,
    context: str = "tourist_walk",
    require_stored_flag: bool = False,
) -> RouteEligibilityVerdict:
    category = canonical_category_for_place(place)
    reasons = tuple(filter(None, (
        _city_reason(city),
        "missing_city_id" if not getattr(place, "city_id", None) else "",
        "inactive" if getattr(place, "is_active", None) is not True else "",
        "place_status_not_active" if getattr(place, "status", "active") not in (None, "active") else "",
        "lifecycle_not_active" if getattr(place, "lifecycle_status", "active") != "active" else "",
        "draft_or_unpublished" if getattr(place, "is_published", None) is not True else "",
        "not_visible_in_catalog" if getattr(place, "is_visible_in_catalog", None) is not True else "",
        "route_eligible_not_true" if require_stored_flag and getattr(place, "is_route_eligible", None) is not True else "",
        _coordinate_reason(place),
        "generic_osm_placeholder" if is_placeholder_title(getattr(place, "title", None)) else "",
        _category_reason(place, category),
        _layer_reason(place),
        _quality_reason(place),
        "spam_poi" if getattr(place, "is_spam_poi", False) else "",
        "duplicate_suspected" if getattr(place, "is_duplicate_suspected", False) else "",
        "critical_field_expired" if getattr(place, "critical_field_expired", False) else "",
        "place_archived" if getattr(place, "publication_status", "published") == "archived" else "",
    )))
    return RouteEligibilityVerdict(not reasons, reasons, category, _admin_bucket(reasons))


def compile_route_eligible_sql_conditions(context: str = "tourist_walk") -> tuple[Any, ...]:
    category_ok = _category_sql_condition()
    return (
        Place.is_active.is_(True), or_(Place.status.is_(None), Place.status == "active"),
        Place.lifecycle_status == "active", Place.is_published.is_(True), Place.is_visible_in_catalog.is_(True),
        Place.is_route_eligible.is_(True), Place.publication_status.in_(PUBLICATION_STATUSES),
        Place.lat.is_not(None), Place.lng.is_not(None), Place.lat != 0.0, Place.lng != 0.0,
        *tuple(not_(Place.title.ilike(pattern)) for pattern in PLACEHOLDER_SQL_PATTERNS),
        category_ok, Place.place_layer.in_(ROUTE_ALLOWED_PLACE_LAYERS), Place.tourist_eligible.is_(True),
        Place.transport_required.is_(False), Place.route_policy.notin_(NON_WALKING_POLICIES),
        Place.quality_tier.in_(tuple(ROUTE_ALLOWED_QUALITY_TIERS)),
        Place.is_spam_poi.is_(False), Place.is_duplicate_suspected.is_(False), Place.critical_field_expired.is_(False),
    )


def _category_sql_condition() -> Any:
    blocked = tuple(HARD_EXCLUDED_CATEGORIES)
    allowed = tuple(ALLOWED_ROUTE_CATEGORIES)
    return or_(
        and_(Place.canonical_category.is_not(None), Place.canonical_category.in_(allowed), Place.canonical_category.notin_(blocked)),
        and_(Place.canonical_category.is_(None), Place.category_ref.has(and_(Category.is_active.is_(True), Category.code.in_(allowed), Category.code.notin_(blocked)))),
    )


def _city_reason(city: Any | None) -> str:
    if city is None:
        return ""
    if getattr(city, "is_active", True) is not True:
        return "city_inactive"
    return "city_not_published" if getattr(city, "launch_status", "published") != "published" else ""


def _coordinate_reason(place: Any) -> str:
    lat, lng = getattr(place, "lat", None), getattr(place, "lng", None)
    if lat is None or lng is None:
        return "missing_coordinates"
    return "invalid_coordinates" if float(lat or 0.0) == 0.0 and float(lng or 0.0) == 0.0 else ""


def _category_reason(place: Any, category: str | None) -> str:
    if not category:
        return "unknown_category"
    if category in HARD_EXCLUDED_CATEGORIES:
        return f"hard_excluded_category:{category}"
    if category not in ALLOWED_ROUTE_CATEGORIES:
        return "unknown_category"
    category_ref = getattr(place, "category_ref", None)
    return "category_inactive" if category_ref is not None and getattr(category_ref, "is_active", True) is not True else ""


def _layer_reason(place: Any) -> str:
    if getattr(place, "place_layer", "tourist_catalog") not in ROUTE_ALLOWED_PLACE_LAYERS:
        return "non_tourist_place_layer"
    if getattr(place, "tourist_eligible", True) is not True:
        return "not_tourist_eligible"
    if getattr(place, "transport_required", False):
        return "transport_required_scope"
    return "non_walking_route_policy" if getattr(place, "route_policy", "city_walking") in NON_WALKING_POLICIES else ""


def _quality_reason(place: Any) -> str:
    tier = str(getattr(place, "quality_tier", "silver") or "").strip().lower()
    return "" if tier in ROUTE_ALLOWED_QUALITY_TIERS else f"quality_tier_not_route_allowed:{tier or 'empty'}"


def _admin_bucket(reasons: tuple[str, ...]) -> str:
    if not reasons:
        return "route_eligible"
    if "unknown_category" in reasons:
        return "route_unknown"
    return "route_excluded"
