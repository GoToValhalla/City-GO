"""
Загрузка готовых маршрутов (Route) с сортировкой route_places по position.

get_routes*/get_route_by_id/get_route_by_slug are internal/admin-safe
helpers with NO publication filter — they are reused by
services/admin_service.py and services/admin_extended_service.py, which
must see and edit unpublished (Route.is_active=False) routes (e.g.
publish_route/unpublish_route themselves load the route via
get_route_by_id before toggling is_active). The public,
unauthenticated GET /routes* endpoints in routers/routes.py must instead
use the get_public_route_*/get_public_routes* variants below, which apply
the Route.is_active publication gate.
"""

from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.route import Route
from models.route_place import RoutePlace


# Все маршруты (без фильтра по городу). Internal/admin-safe — без publication-фильтра.
def get_routes(db: Session) -> list[Route]:
    return db.query(Route).all()


# Маршруты одного города по city_id. Internal/admin-safe — без publication-фильтра.
def get_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    return db.query(Route).filter(Route.city_id == city_id).all()


# Маршруты города по slug (если город не найден — пустой список). Internal/admin-safe.
def get_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    return db.query(Route).filter(Route.city_id == city.id).all()


# Детальный маршрут с подгруженными местами; точки упорядочены по position.
# Internal/admin-safe — без publication-фильтра.
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


# То же, что get_route_by_id, но поиск по slug маршрута. Internal/admin-safe.
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


# --- Public (publication-gated) variants used by routers/routes.py ---------


# Все опубликованные маршруты (без фильтра по городу).
def get_public_routes(db: Session) -> list[Route]:
    return db.query(Route).filter(Route.is_active.is_(True)).all()


# Опубликованные маршруты одного города по city_id.
def get_public_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    return db.query(Route).filter(Route.city_id == city_id, Route.is_active.is_(True)).all()


# Опубликованные маршруты города по slug (если город не найден — пустой список).
def get_public_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    return db.query(Route).filter(Route.city_id == city.id, Route.is_active.is_(True)).all()


# Детальный опубликованный маршрут с подгруженными местами; точки упорядочены по position.
def get_public_route_by_id(db: Session, route_id: int) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.id == route_id, Route.is_active.is_(True))
        .first()
    )

    if route is None:
        return None

    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


# То же, что get_public_route_by_id, но поиск по slug маршрута.
def get_public_route_by_slug(db: Session, slug: str) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.slug == slug, Route.is_active.is_(True))
        .first()
    )

    if route is None:
        return None

    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


# Сериализация точек маршрута для ответа API (slug/title места).
def build_route_points(route: Route) -> list[dict]:
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
