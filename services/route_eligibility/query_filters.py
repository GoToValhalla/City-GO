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

    Важно: route generation не должен схлопываться из-за неполного enrichment.
    Для городов на этапе заполнения данных публичное route-visible место с координатами
    лучше, чем пустой маршрут. Поэтому SQL-eligibility оставляет только настоящие hard
    constraints:

    - место публично и доступно для маршрутов;
    - есть координаты;
    - категория не входит в технический/запрещённый список.

    Data-quality поля вроде quality_tier, lifecycle_status, critical_field_expired,
    duplicate/spam flags и canonical_category не должны быть hard blocker на этапе
    candidate retrieval. Их нужно учитывать ниже как quality signals/warnings, иначе
    город с 215 route-visible местами превращается в 19 кандидатов и no_route.
    """
    return (
        *public_route_place_conditions(),
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        or_(
            Place.canonical_category.is_(None),
            Place.canonical_category.notin_(tuple(ROUTE_FORBIDDEN_CATEGORIES)),
        ),
        or_(
            Place.category.is_(None),
            Place.category.notin_(tuple(ROUTE_FORBIDDEN_CATEGORIES)),
        ),
    )


def apply_route_eligible_filters(query: Query) -> Query:
    return query.filter(*route_eligible_sql_conditions())


def is_route_forbidden_category(category: str | None) -> bool:
    return bool(category and category.strip().lower() in ROUTE_FORBIDDEN_CATEGORIES)
