"""
Связи маршрута с местами (порядок точек в Route).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_place import RoutePlaceRead
from services.route_place_service import get_route_places, get_route_places_by_route_id

router = APIRouter(prefix="/route-places", tags=["route-places"])


# Возвращает список всех связей маршрутов и мест.
# Если передан route_id, возвращает связи только для выбранного маршрута.
@router.get("/", response_model=list[RoutePlaceRead])
def read_route_places(
    route_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RoutePlaceRead]:
    if route_id is not None:
        return get_route_places_by_route_id(db, route_id)
    return get_route_places(db)
