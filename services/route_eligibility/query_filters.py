"""SQL-фильтры route eligibility для candidate query."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place
from services.place_public_visibility import public_route_place_conditions
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Возвращает единый SQL-фильтр видимости мест для маршрутов.

    Важно: публичная витрина и диагностика маршрутов допускают NULL в legacy-флагах
    is_active/status/is_published/is_visible_in_catalog/is_route_eligible. После импортов
    старые записи часто не имеют этих флагов, поэтому строгие `is_(True)` здесь давали
    расхождение: diagnostic geo_query_count видел сотни мест, а реальный retrieval — 0.
    """
    return (
        *public_route_place_conditions(),
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
