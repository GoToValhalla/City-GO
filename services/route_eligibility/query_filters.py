"""SQL-фильтры route eligibility для candidate query."""

from __future__ import annotations

from typing import Any

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from models.place import Place

from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    return (
        Place.is_active.is_(True),
        Place.status == "active",
        Place.is_published.is_(True),
        Place.is_visible_in_catalog.is_(True),
        Place.is_route_eligible.is_(True),
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        or_(
            Place.category.is_(None),
            Place.category.notin_(tuple(ROUTE_FORBIDDEN_CATEGORIES)),
        ),
    )


def apply_route_eligible_filters(query: Query) -> Query:
    return query.filter(*route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in ROUTE_FORBIDDEN_CATEGORIES)
