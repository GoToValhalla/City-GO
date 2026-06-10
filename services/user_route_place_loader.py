from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import UserRouteState
from services.place_public_visibility import apply_public_place_visibility


def load_ordered_places(db: Session, route: UserRouteState) -> list[Place]:
    ids = [int(point.place_id) for point in route.points if point.place_id.isdigit()]
    if not ids:
        return []

    query = db.query(Place).filter(Place.id.in_(ids))
    places = apply_public_place_visibility(query).all()

    by_id = {int(place.id): place for place in places}
    return [by_id[place_id] for place_id in ids if place_id in by_id]


def load_place(db: Session, place_id: str | None) -> Place | None:
    if place_id is None or not place_id.isdigit():
        return None

    query = db.query(Place).filter(Place.id == int(place_id))
    return apply_public_place_visibility(query).first()