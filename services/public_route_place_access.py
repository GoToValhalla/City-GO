from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable

from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from schemas.user_route import UserRouteIntent, UserRouteState
from services.route_eligibility import apply_public_route_eligible_filters


@dataclass(frozen=True)
class PublicRouteScope:
    city_id: int
    city_slug: str


def resolve_public_city_scope(db: Session, city_slug: str | None) -> PublicRouteScope | None:
    """Resolve a public city slug to one typed database scope."""
    slug = str(city_slug or "").strip()
    if not slug:
        return None
    row = (
        db.query(City.id, City.slug)
        .filter(
            City.slug == slug,
            City.is_active.is_(True),
            City.launch_status == "published",
        )
        .first()
    )
    return PublicRouteScope(city_id=int(row.id), city_slug=str(row.slug)) if row is not None else None


def resolve_intent_scope(db: Session, intent: UserRouteIntent) -> PublicRouteScope | None:
    return resolve_public_city_scope(db, intent.city_id)


def resolve_route_scope(db: Session, route: UserRouteState) -> PublicRouteScope | None:
    """Validate the complete route identity and derive one authoritative scope.

    Every point ID must be a unique positive decimal ID, every row must exist, all
    rows must belong to one active published city, and an explicit context city
    slug must resolve to that same city. Any inconsistency invalidates the whole
    route instead of silently dropping or re-scoping points.
    """
    raw_ids = [point.place_id for point in route.points]
    if not raw_ids:
        return resolve_intent_scope(db, route.context)

    ids = _strict_numeric_ids(raw_ids)
    if ids is None or len(set(ids)) != len(ids):
        return None

    rows = db.query(Place.id, Place.city_id).filter(Place.id.in_(ids)).all()
    if len(rows) != len(ids) or any(row.city_id is None for row in rows):
        return None
    city_ids = {int(row.city_id) for row in rows}
    if len(city_ids) != 1:
        return None

    city_id = next(iter(city_ids))
    row = (
        db.query(City.id, City.slug)
        .filter(
            City.id == city_id,
            City.is_active.is_(True),
            City.launch_status == "published",
        )
        .first()
    )
    if row is None:
        return None

    scope = PublicRouteScope(city_id=int(row.id), city_slug=str(row.slug))
    context_slug = str(route.context.city_id or "").strip()
    if context_slug:
        context_scope = resolve_public_city_scope(db, context_slug)
        if context_scope != scope:
            return None
    return scope


def public_route_place_query(db: Session, *, scope: PublicRouteScope | None) -> Query:
    """The only public route-place query constructor."""
    query = apply_public_route_eligible_filters(db.query(Place))
    if scope is None:
        return query.filter(False)
    return query.filter(Place.city_id == scope.city_id)


def load_public_route_place(
    db: Session,
    place_id: str | None,
    *,
    scope: PublicRouteScope | None,
) -> Place | None:
    parsed = _strict_numeric_ids([place_id])
    if parsed is None:
        return None
    return public_route_place_query(db, scope=scope).filter(Place.id == parsed[0]).first()


def load_public_route_places(
    db: Session,
    place_ids: list[str],
    *,
    scope: PublicRouteScope | None,
) -> list[Place]:
    ids = _strict_numeric_ids(place_ids)
    if ids is None or not ids or len(set(ids)) != len(ids) or scope is None:
        return []
    places = public_route_place_query(db, scope=scope).filter(Place.id.in_(ids)).all()
    if len(places) != len(ids):
        return []
    by_id = {int(place.id): place for place in places}
    return [by_id[place_id] for place_id in ids]


def _strict_numeric_ids(values: Iterable[object]) -> list[int] | None:
    result: list[int] = []
    for value in values:
        if not isinstance(value, str) or not value.isdigit():
            return None
        parsed = int(value)
        if parsed <= 0:
            return None
        result.append(parsed)
    return result
