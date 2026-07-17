from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import UserRouteState
from services.place_staleness_policy import is_route_usable_place
from services.public_route_place_access import apply_public_route_city_scope, resolve_route_city_id
from services.route_geometry import distance_meters


def find_replacement_place(
    db: Session,
    *,
    route: UserRouteState,
    category: str | None,
    excluded_ids: set[str],
) -> Place | None:
    candidates = _query_candidates(db, route)
    filtered = tuple(filter(lambda place: _usable(place, category, excluded_ids), candidates))
    return min(filtered, key=lambda place: _distance_from_start(place, route), default=None)


def _query_candidates(db: Session, route: UserRouteState) -> list[Place]:
    city_id = resolve_route_city_id(db, route)
    query = apply_public_route_city_scope(db.query(Place), city_id=city_id)
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


def _distance_from_start(place: Place, route: UserRouteState) -> float:
    ctx = route.context
    return distance_meters(float(ctx.lat or 0.0), float(ctx.lng or 0.0), float(place.lat), float(place.lng))
