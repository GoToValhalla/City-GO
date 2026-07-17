from __future__ import annotations

from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from schemas.user_route import UserRouteIntent, UserRouteState
from services.route_eligibility import apply_public_route_eligible_filters


def resolve_public_city_id(db: Session, city_slug: str | None) -> int | None:
    """Resolve a public city slug to its database ID, fail closed otherwise."""
    if not city_slug:
        return None
    row = (
        db.query(City.id)
        .filter(
            City.slug == city_slug,
            City.is_active.is_(True),
            City.launch_status == "published",
        )
        .first()
    )
    return int(row[0]) if row is not None else None


def resolve_intent_city_id(db: Session, intent: UserRouteIntent) -> int | None:
    return resolve_public_city_id(db, intent.city_id)


def resolve_route_city_id(db: Session, route: UserRouteState) -> int | None:
    """Derive one authoritative city scope from DB rows referenced by a route.

    Client-supplied point.city_slug is never trusted. Existing point IDs must all
    exist and belong to exactly one city. For an empty route, the public city slug
    in route.context is resolved through the database.
    """
    ids = _numeric_ids(point.place_id for point in route.points)
    if not ids:
        return resolve_intent_city_id(db, route.context)

    unique_ids = set(ids)
    rows = db.query(Place.id, Place.city_id).filter(Place.id.in_(unique_ids)).all()
    if len(rows) != len(unique_ids):
        return None
    city_ids = {int(row.city_id) for row in rows if row.city_id is not None}
    if len(city_ids) != 1:
        return None

    city_id = next(iter(city_ids))
    public_city = (
        db.query(City.id)
        .filter(
            City.id == city_id,
            City.is_active.is_(True),
            City.launch_status == "published",
        )
        .first()
    )
    return city_id if public_city is not None else None


def apply_public_route_city_scope(query: Query, *, city_id: int | None) -> Query:
    """Apply the complete public route contract plus one authoritative city."""
    query = apply_public_route_eligible_filters(query)
    if city_id is None:
        return query.filter(False)
    return query.filter(Place.city_id == city_id)


def load_public_route_place(db: Session, place_id: str | None, *, city_id: int | None) -> Place | None:
    if place_id is None or not place_id.isdigit():
        return None
    query = db.query(Place).filter(Place.id == int(place_id))
    return apply_public_route_city_scope(query, city_id=city_id).first()


def load_public_route_places(db: Session, place_ids: list[str], *, city_id: int | None) -> list[Place]:
    ids = _numeric_ids(place_ids)
    if not ids or city_id is None:
        return []
    places = apply_public_route_city_scope(
        db.query(Place).filter(Place.id.in_(set(ids))),
        city_id=city_id,
    ).all()
    by_id = {int(place.id): place for place in places}
    return [by_id[place_id] for place_id in ids if place_id in by_id]


def _numeric_ids(values) -> list[int]:
    return [int(value) for value in values if isinstance(value, str) and value.isdigit()]
