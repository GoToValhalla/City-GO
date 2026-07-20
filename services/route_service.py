"""
Загрузка готовых маршрутов (Route) с сортировкой route_places по position.

get_routes*/get_route_by_id/get_route_by_slug are internal/admin-safe
helpers with NO publication filter — they are reused by
services/admin_service.py and services/admin_extended_service.py, which
must see and edit unpublished (Route.is_active=False) routes (e.g.
publish_route/unpublish_route themselves load the route via
get_route_by_id before toggling is_active). The public,
unauthenticated GET /routes* endpoints in routers/routes.py must instead
use the get_public_route_*/get_public_routes* variants below.
"""

from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.route import Route
from models.route_place import RoutePlace
from services.public_editorial_route_access import (
    is_public_editorial_route_visible,
    load_public_editorial_route_query,
    public_editorial_route_places,
)


def get_routes(db: Session) -> list[Route]:
    return db.query(Route).all()


def get_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    return db.query(Route).filter(Route.city_id == city_id).all()


def get_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []
    return db.query(Route).filter(Route.city_id == city.id).all()


def get_route_by_id(db: Session, route_id: int) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.id == route_id)
        .first()
    )
    if route is None:
        return None
    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


def get_route_by_slug(db: Session, slug: str) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.slug == slug)
        .first()
    )
    if route is None:
        return None
    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


def get_public_routes(db: Session) -> list[Route]:
    routes = load_public_editorial_route_query(db).all()
    return [route for route in routes if is_public_editorial_route_visible(db, route)]


def get_public_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    routes = load_public_editorial_route_query(db).filter(Route.city_id == city_id).all()
    return [route for route in routes if is_public_editorial_route_visible(db, route)]


def get_public_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []
    return get_public_routes_by_city_id(db, city.id)


def get_public_route_by_id(db: Session, route_id: int) -> Route | None:
    route = load_public_editorial_route_query(db).filter(Route.id == route_id).first()
    if route is None or not is_public_editorial_route_visible(db, route):
        return None
    route.route_places = public_editorial_route_places(db, route)
    return route


def get_public_route_by_slug(db: Session, slug: str) -> Route | None:
    route = load_public_editorial_route_query(db).filter(Route.slug == slug).first()
    if route is None or not is_public_editorial_route_visible(db, route):
        return None
    route.route_places = public_editorial_route_places(db, route)
    return route


def build_route_points(route: Route) -> list[dict]:
    """Serialize ALL persisted points (admin/internal). Public callers must
    use get_public_route_* which already replaces route_places with eligible ones."""
    points: list[dict] = []
    for item in sorted(route.route_places, key=lambda row: row.position):
        place = item.place
        points.append(
            {
                "place_id": item.place_id,
                "position": item.position,
                "place_slug": place.slug if place else None,
                "place_title": place.title if place else None,
                "lat": place.lat if place else None,
                "lng": place.lng if place else None,
                "category": place.category if place else None,
                "address": place.address if place else None,
                "is_published": place.is_published if place else None,
                "is_route_eligible": place.is_route_eligible if place else None,
                "publication_status": place.publication_status if place else None,
                "is_active": place.is_active if place else None,
                "status": place.status if place else None,
            }
        )
    return points
