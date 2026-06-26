"""SQL filters for route eligibility candidate queries."""

from __future__ import annotations

from typing import Any

from sqlalchemy import not_, or_
from sqlalchemy.orm import Query

from models.place import Place
from services.place_public_visibility import (
    admin_preview_route_place_conditions,
    public_route_place_conditions,
)
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES
from services.route_policy_service import evaluate_category_policy


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Eligibility conditions for user-facing routes."""

    return _route_eligible_conditions(public_route_place_conditions())


def admin_preview_route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Eligibility conditions for an authenticated admin preview."""

    return _route_eligible_conditions(admin_preview_route_place_conditions())


def _route_eligible_conditions(place_conditions: tuple[Any, ...]) -> tuple[Any, ...]:
    blocked = tuple(ROUTE_FORBIDDEN_CATEGORIES)
    return (
        *place_conditions,
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        *placeholder_title_sql_conditions(),
        or_(Place.canonical_category.is_(None), Place.canonical_category.notin_(blocked)),
        or_(Place.category.is_(None), Place.category.notin_(blocked)),
    )


def placeholder_title_sql_conditions() -> tuple[Any, ...]:
    return tuple(not_(Place.title.ilike(pattern)) for pattern in PLACEHOLDER_SQL_PATTERNS)


def apply_route_eligible_filters(query: Query) -> Query:
    return query.filter(*route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in ROUTE_FORBIDDEN_CATEGORIES)


def is_route_category_allowed(category: object, context: str = "tourist_walk") -> bool:
    return evaluate_category_policy(category, context=context)
