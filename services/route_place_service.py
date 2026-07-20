"""
Связь many-to-many маршрут ↔ место (позиция в маршруте).

Public-only module: callers are routers/route_places.py. Applies the same
fail-closed editorial boundary as get_public_route_* (active route,
published city, currently public-route-eligible places).
"""

from sqlalchemy.orm import Session, joinedload

from models.route import Route
from models.route_place import RoutePlace
from services.public_editorial_route_access import (
    is_public_editorial_route_visible,
    load_public_editorial_route_query,
    public_editorial_route_places,
)


def get_route_places(db: Session) -> list[RoutePlace]:
    routes = load_public_editorial_route_query(db).all()
    visible = [route for route in routes if is_public_editorial_route_visible(db, route)]
    points: list[RoutePlace] = []
    for route in visible:
        points.extend(public_editorial_route_places(db, route))
    return points


def get_route_places_by_route_id(db: Session, route_id: int) -> list[RoutePlace]:
    route = (
        load_public_editorial_route_query(db)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.id == route_id)
        .first()
    )
    if route is None or not is_public_editorial_route_visible(db, route):
        return []
    return public_editorial_route_places(db, route)
