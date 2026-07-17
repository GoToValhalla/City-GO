from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import UserRouteState
from services.public_route_place_access import (
    load_public_route_place,
    load_public_route_places,
    resolve_route_city_id,
)


def load_ordered_places(db: Session, route: UserRouteState) -> list[Place]:
    city_id = resolve_route_city_id(db, route)
    return load_public_route_places(
        db,
        [point.place_id for point in route.points],
        city_id=city_id,
    )


def load_place(db: Session, place_id: str | None, *, city_id: int | None = None) -> Place | None:
    return load_public_route_place(db, place_id, city_id=city_id)
