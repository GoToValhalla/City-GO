from __future__ import annotations

from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place

PUBLIC_ACTIVE_STATUS = "active"

PUBLIC_HIDDEN_CATEGORIES = {
    "transport",
    "useful",
    "fuel",
    "parking",
    "bank",
    "atm",
    "car_service",
}


def public_place_conditions() -> tuple[Any, ...]:
    return (
        _true_or_null(Place.is_active),
        or_(Place.status.is_(None), Place.status == PUBLIC_ACTIVE_STATUS),
        _true_or_null(Place.is_published),
        _true_or_null(Place.is_visible_in_catalog),
        or_(
            Place.category.is_(None),
            Place.category.notin_(tuple(PUBLIC_HIDDEN_CATEGORIES)),
        ),
    )


def public_route_place_conditions() -> tuple[Any, ...]:
    return (*public_place_conditions(), _true_or_null(Place.is_route_eligible))


def apply_public_place_visibility(query: Query) -> Query:
    return query.filter(*public_place_conditions())


def apply_public_route_place_visibility(query: Query) -> Query:
    return query.filter(*public_route_place_conditions())


def is_public_hidden_category(category: str | None) -> bool:
    return bool(category in PUBLIC_HIDDEN_CATEGORIES)


def _true_or_null(column: Any) -> Any:
    return or_(column.is_(True), column.is_(None))
