"""
Связь many-to-many маршрут ↔ место (позиция в маршруте).
"""

from sqlalchemy.orm import Session

from models.route_place import RoutePlace


# Возвращает список всех связей маршрутов и мест.
def get_route_places(db: Session) -> list[RoutePlace]:
    return db.query(RoutePlace).all()


# Возвращает список связей по идентификатору маршрута.
def get_route_places_by_route_id(db: Session, route_id: int) -> list[RoutePlace]:
    return (
        db.query(RoutePlace)
        .filter(RoutePlace.route_id == route_id)
        .order_by(RoutePlace.position.asc())
        .all()
    )
