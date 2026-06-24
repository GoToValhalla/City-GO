"""SQL-фильтры route eligibility для candidate query."""

from __future__ import annotations
from typing import Any
from sqlalchemy import not_
from sqlalchemy.orm import Query
from models.place import Place
from services.place_public_visibility import public_route_place_conditions
from services.place_quality_signals import PLACEHOLDER_SQL_PATTERNS
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES
from services.route_policy_service import evaluate_category_policy


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Hard constraints; категорийная политика materialized в Place.is_route_eligible."""
    return (*public_route_place_conditions(), Place.lat.is_not(None), Place.lng.is_not(None), *placeholder_title_sql_conditions())


def placeholder_title_sql_conditions() -> tuple[Any, ...]:
    return tuple(not_(Place.title.ilike(pattern)) for pattern in PLACEHOLDER_SQL_PATTERNS)


def apply_route_eligible_filters(query: Query) -> Query:
    return query.filter(*route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    """Backward-compatible helper для старых diagnostics; runtime evaluator использует Category.route_policy."""
    return bool(category and category.strip().lower() in ROUTE_FORBIDDEN_CATEGORIES)


def is_route_category_allowed(category: object, context: str = "tourist_walk") -> bool:
    return evaluate_category_policy(category, context=context).allowed
