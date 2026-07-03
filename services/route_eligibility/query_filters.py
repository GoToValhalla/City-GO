"""Deprecated SQL wrappers for the CITYGO-171 route eligibility policy."""

from __future__ import annotations

from typing import Any

from sqlalchemy import not_
from sqlalchemy.orm import Query

from models.place import Place
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES, compile_route_eligible_sql_conditions
from services.route_policy_service import evaluate_category_policy


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Eligibility conditions for user-facing routes."""

    return compile_route_eligible_sql_conditions(context="tourist_walk")


def admin_preview_route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Eligibility conditions for an authenticated admin preview."""

    return compile_route_eligible_sql_conditions(context="tourist_walk")


def placeholder_title_sql_conditions() -> tuple[Any, ...]:
    return tuple(not_(Place.title.ilike(pattern)) for pattern in PLACEHOLDER_SQL_PATTERNS)


def apply_route_eligible_filters(query: Query) -> Query:
    return query.filter(*route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in HARD_EXCLUDED_CATEGORIES)


def is_route_category_allowed(category: object, context: str = "tourist_walk") -> bool:
    return evaluate_category_policy(category, context=context)
