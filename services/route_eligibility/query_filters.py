"""SQL-фильтры route eligibility для candidate query."""

from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place
from services.data_foundation_policy import ROUTE_ALLOWED_QUALITY_TIERS
from services.place_public_visibility import public_route_place_conditions
from services.route_eligibility.forbidden_categories import ROUTE_FORBIDDEN_CATEGORIES


def route_eligible_sql_conditions() -> tuple[Any, ...]:
    """Возвращает единый SQL-фильтр видимости мест для маршрутов.

    Data Foundation P0 меняет contract: в маршруты допускаются только active Gold/Silver
    места без spam/duplicate/expired critical fields. Legacy NULL fallback сохранён там,
    где старые записи ещё не мигрированы, но новые поля имеют безопасные defaults.
    """
    return (
        *public_route_place_conditions(),
        Place.lat.is_not(None),
        Place.lng.is_not(None),
        Place.lifecycle_status == "active",
        Place.quality_tier.in_(tuple(ROUTE_ALLOWED_QUALITY_TIERS)),
        Place.is_spam_poi.is_(False),
        Place.is_duplicate_suspected.is_(False),
        Place.critical_field_expired.is_(False),
        or_(
            Place.canonical_category.is_not(None),
            Place.category.is_not(None),
        ),
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
