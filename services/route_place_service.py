"""
Связь many-to-many маршрут ↔ место (позиция в маршруте).
"""

from sqlalchemy.orm import Session

from models.route import Route
from models.route_place import RoutePlace


# Возвращает список всех связей маршрутов и мест. Публичный доступ — только
# для опубликованных маршрутов (Route.is_active is the publication gate
# toggled by services.admin_service.publish_route/unpublish_route).
def get_route_places(db: Session) -> list[RoutePlace]:
    return (
        db.query(RoutePlace)
        .join(Route, RoutePlace.route_id == Route.id)
        .filter(Route.is_active.is_(True))
        .all()
    )


# Возвращает список связей по идентификатору маршрута. Публичный доступ —
# только для опубликованного маршрута.
def get_route_places_by_route_id(db: Session, route_id: int) -> list[RoutePlace]:
    return (
        db.query(RoutePlace)
        .join(Route, RoutePlace.route_id == Route.id)
        .filter(RoutePlace.route_id == route_id, Route.is_active.is_(True))
        .order_by(RoutePlace.position.asc())
        .all()
    )
