from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from models.city import City
from models.place import Place
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

PUBLIC_ACTIVE_STATUS = "active"

PUBLIC_HIDDEN_CATEGORIES = {
    "transport",
    "useful",
    "fuel",
    "parking",
    "bank",
    "atm",
    "car_service",
    "health",
    "medical",
    "pharmacy",
}

PUBLIC_HIDDEN_CATEGORIES = PUBLIC_HIDDEN_CATEGORIES | HARD_EXCLUDED_CATEGORIES


def public_place_conditions() -> tuple[Any, ...]:
    return (
        Place.city.has(and_(City.is_active.is_(True), City.launch_status == "published")),
        *admin_preview_place_conditions(),
    )


def admin_preview_place_conditions() -> tuple[Any, ...]:
    """Place gates for administrative previews; city publication is intentionally excluded."""

    return (
        Place.is_active.is_(True),
        or_(Place.status.is_(None), Place.status == PUBLIC_ACTIVE_STATUS),
        Place.is_published.is_(True),
        Place.is_visible_in_catalog.is_(True),
        or_(
            Place.canonical_category.is_(None),
            Place.canonical_category.notin_(tuple(PUBLIC_HIDDEN_CATEGORIES)),
        ),
    )


def public_route_place_conditions() -> tuple[Any, ...]:
    return (*public_place_conditions(), Place.is_route_eligible.is_(True))


def admin_preview_route_place_conditions() -> tuple[Any, ...]:
    return (*admin_preview_place_conditions(), Place.is_route_eligible.is_(True))

def apply_public_place_visibility(query: Query) -> Query:
    return query.filter(*public_place_conditions())


def apply_public_route_place_visibility(query: Query) -> Query:
    return query.filter(*public_route_place_conditions())


def is_public_hidden_category(category: str | None) -> bool:
    return bool(category in PUBLIC_HIDDEN_CATEGORIES)


def _true_or_null(column: Any) -> Any:
    return or_(column.is_(True), column.is_(None))
