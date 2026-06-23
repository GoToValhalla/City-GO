"""
Загрузка готовых маршрутов (Route) с сортировкой route_places по position.
"""

from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.route import Route
from models.route_place import RoutePlace


# Все маршруты (без фильтра по городу).
def get_routes(db: Session) -> list[Route]:
    return db.query(Route).all()


# Маршруты одного города по city_id.
def get_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    return db.query(Route).filter(Route.city_id == city_id).all()


# Маршруты города по slug (если город не найден — пустой список).
def get_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    return db.query(Route).filter(Route.city_id == city.id).all()


# Детальный маршрут с подгруженными местами; точки упорядочены по position.
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


# То же, что get_route_by_id, но поиск по slug маршрута.
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
