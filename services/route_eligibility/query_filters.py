"""SQL query contracts for route eligibility."""

from __future__ import annotations

from typing import Any

from sqlalchemy import not_
from sqlalchemy.orm import Query

from models.place import Place
from services.place_public_visibility import public_place_conditions
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES, compile_route_eligible_sql_conditions
from services.route_policy_service import evaluate_category_policy


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Place-level eligibility conditions shared by public and admin flows."""

    return compile_route_eligible_sql_conditions(context="tourist_walk")


def public_route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Complete public route-place contract.

    Public route selection must satisfy both the public publication boundary
    (active published city and publicly visible place) and the route-specific
    eligibility policy. Keeping the composition here prevents callers from
    accidentally applying only one half of the contract.
    """

    return (*public_place_conditions(), *route_eligible_sql_conditions())


def admin_preview_route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Place-level eligibility for authenticated admin preview flows.

    City publication is intentionally not required here; public callers must
    use public_route_eligible_sql_conditions() instead.
    """

    return route_eligible_sql_conditions()


def placeholder_title_sql_conditions() -> tuple[Any, ...]:
    return tuple(not_(Place.title.ilike(pattern)) for pattern in PLACEHOLDER_SQL_PATTERNS)


def apply_route_eligible_filters(query: Query) -> Query:
    """Apply place-level eligibility only.

    Reserved for non-public policy evaluation and authenticated admin preview.
    Public route entrypoints must use apply_public_route_eligible_filters().
    """

    return query.filter(*route_eligible_sql_conditions())


def apply_public_route_eligible_filters(query: Query) -> Query:
    """Apply the canonical complete public route-place contract."""

    return query.filter(*public_route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in HARD_EXCLUDED_CATEGORIES)


def is_route_category_allowed(category: object, context: str = "tourist_walk") -> bool:
    return evaluate_category_policy(category, context=context)
