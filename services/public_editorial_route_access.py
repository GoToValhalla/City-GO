"""Public editorial Route access: city + place contract (Stage 3)."""

from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.place import Place
from models.route import Route
from models.route_place import RoutePlace
from services.route_eligibility import public_route_eligible_sql_conditions

MIN_PUBLIC_EDITORIAL_POINTS = 2


def public_city_filters() -> tuple:
    return (City.is_active.is_(True), City.launch_status == "published")


def eligible_place_ids_among(db: Session, place_ids: list[int]) -> set[int]:
    if not place_ids:
        return set()
    rows = (
        db.query(Place.id)
        .join(City, Place.city_id == City.id)
        .filter(Place.id.in_(place_ids), *public_route_eligible_sql_conditions())
        .all()
    )
    return {int(row[0]) for row in rows}


def public_editorial_route_places(db: Session, route: Route) -> list[RoutePlace]:
    place_ids = [int(item.place_id) for item in route.route_places]
    eligible = eligible_place_ids_among(db, place_ids)
    return [
        item
        for item in sorted(route.route_places, key=lambda row: row.position)
        if int(item.place_id) in eligible
    ]


def is_public_editorial_route_visible(db: Session, route: Route) -> bool:
    """Fail-closed: active route, published city, ≥2 currently eligible points."""
    if not bool(route.is_active):
        return False
    city = route.city
    if city is None:
        city = db.query(City).filter(City.id == route.city_id).first()
    if city is None or not bool(city.is_active) or city.launch_status != "published":
        return False
    return len(public_editorial_route_places(db, route)) >= MIN_PUBLIC_EDITORIAL_POINTS


def load_public_editorial_route_query(db: Session):
    return (
        db.query(Route)
        .join(City, Route.city_id == City.id)
        .options(
            joinedload(Route.route_places).joinedload(RoutePlace.place),
            joinedload(Route.city),
        )
        .filter(Route.is_active.is_(True), *public_city_filters())
    )
