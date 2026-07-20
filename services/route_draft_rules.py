from __future__ import annotations

import re
from unicodedata import normalize as unicode_normalize

from sqlalchemy.orm import Query

from models.city import City
from models.place import Place
from services.route_eligibility import public_route_eligible_sql_conditions
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

WALK_SPEED_KMH = 4.5
OUT_OF_CITY_MAX_METERS = 50_000
ROUTE_DRAFT_BLOCKED_CATEGORIES = HARD_EXCLUDED_CATEGORIES

CATEGORY_ALIASES: dict[str, str] = {
    "кофе": "cafe",
    "кофейня": "cafe",
    "кафэ": "cafe",
    "coffee": "cafe",
    "музей": "museum",
    "выставка": "museum",
    "парк": "park",
    "сквер": "park",
    "прогулка": "walk",
    "гулять": "walk",
    "еда": "food",
    "поесть": "food",
    "ресторан": "food",
}


def warning(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def normalize_text(value: str | None) -> str:
    raw = unicode_normalize("NFKD", value or "").casefold()
    return re.sub(r"[^a-zа-я0-9]+", " ", raw).strip()


def category_for_query(query: str | None) -> str | None:
    normalized = normalize_text(query)
    return CATEGORY_ALIASES.get(normalized)


def eligible_place_query(query: Query, city_id: int) -> Query:
    """Public, unauthenticated random/draft route entrypoints must use the
    complete public route contract (city publication + place visibility +
    place-level eligibility), not place-level eligibility alone — see
    services.route_eligibility.public_route_eligible_sql_conditions."""
    return query.join(City, Place.city_id == City.id).filter(
        Place.city_id == city_id,
        *public_route_eligible_sql_conditions(),
    )


def visit_minutes_for(place: Place) -> int:
    if place.average_visit_duration_minutes:
        return int(place.average_visit_duration_minutes)
    return {"cafe": 25, "coffee": 25, "museum": 45, "park": 30, "walk": 30}.get(place.category or "", 35)


def target_points_for(budget_minutes: int) -> int:
    if budget_minutes <= 75:
        return 3
    if budget_minutes <= 135:
        return 5
    return 7
