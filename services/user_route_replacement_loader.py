from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from services.place_staleness_policy import is_route_usable_place
from services.route_eligibility import apply_route_eligible_filters
from services.route_geometry import distance_meters


def find_replacement_place(
    db: Session,
    *,
    route: object,
    category: str | None,
    excluded_ids: set[str],
) -> Place | None:
    candidates = _query_candidates(db, route)
    filtered = tuple(filter(lambda place: _usable(place, category, excluded_ids), candidates))
    return min(filtered, key=lambda place: _distance_from_start(place, route), default=None)


def _query_candidates(db: Session, route: object) -> list[Place]:
    query = db.query(Place)

    city_id = getattr(getattr(route, "context", None), "city_id", None)
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)

    query = apply_route_eligible_filters(query)

    return list(query.all())


def _usable(place: Place, category: str | None, excluded_ids: set[str]) -> bool:
    return (
        is_route_usable_place(place)
        and _has_coordinates(place)
        and str(place.id) not in excluded_ids
        and _category_matches(place, category)
    )


def _category_matches(place: Place, category: str | None) -> bool:
    return True if category is None else str(getattr(place, "category", "") or "") == category


def _has_coordinates(place: Place) -> bool:
    return isinstance(getattr(place, "lat", None), (int, float)) and isinstance(getattr(place, "lng", None), (int, float))


def _distance_from_start(place: Place, route: object) -> float:
    ctx = getattr(route, "context", None)
    lat = float(getattr(ctx, "lat", 0.0) or 0.0)
    lng = float(getattr(ctx, "lng", 0.0) or 0.0)
    return distance_meters(lat, lng, float(place.lat), float(place.lng))