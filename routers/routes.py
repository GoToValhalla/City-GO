"""
Готовые editorial-маршруты (модель Route) с точками и пешеходная геометрия.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route import RouteDetailRead, RouteRead
from schemas.walking_route import WalkingRouteRequest, WalkingRouteResponse
from services.route_service import (
    build_route_points,
    get_route_by_id,
    get_route_by_slug,
    get_routes,
    get_routes_by_city_id,
    get_routes_by_city_slug,
)
from services.walking_route_service import build_walking_route

router = APIRouter(prefix="/routes", tags=["routes"])


@router.post("/walking-geometry", response_model=WalkingRouteResponse)
def create_walking_geometry(payload: WalkingRouteRequest) -> WalkingRouteResponse:
    """Route ordered stops over the pedestrian street/path graph."""
    return build_walking_route(payload.points)


@router.get("/", response_model=list[RouteRead])
def read_routes(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RouteRead]:
    if city_slug is not None:
        return get_routes_by_city_slug(db, city_slug)

    if city_id is not None:
        return get_routes_by_city_id(db, city_id)

    return get_routes(db)


@router.get("/by-slug/{slug}", response_model=RouteDetailRead)
def read_route_by_slug(slug: str, db: Session = Depends(get_db)) -> RouteDetailRead:
    route = get_route_by_slug(db, slug)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteDetailRead(
        id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        distance_km=route.distance_km,
        route_mode=route.route_mode,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
        points=build_route_points(route),
    )


@router.get("/{route_id}", response_model=RouteDetailRead)
def read_route(route_id: int, db: Session = Depends(get_db)) -> RouteDetailRead:
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteDetailRead(
        id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        distance_km=route.distance_km,
        route_mode=route.route_mode,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
        points=build_route_points(route),
    )