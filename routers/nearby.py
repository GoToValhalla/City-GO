"""
Места в радиусе от переданных lat/lng (см. nearby_service).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.nearby import NearbyPlaceRead, NearestCityRead
from services.nearby_service import get_nearby_places, nearest_city

router = APIRouter(prefix="/nearby", tags=["nearby"])


# Возвращает список мест рядом с переданной точкой.
@router.get("/", response_model=list[NearbyPlaceRead])
def read_nearby_places(
    lat: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lng: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
    radius_km: float = Query(default=3.0, ge=0.1, le=50, allow_inf_nan=False),
    db: Session = Depends(get_db),
) -> list[NearbyPlaceRead]:
    _reject_null_island(lat, lng)
    return get_nearby_places(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )


@router.get("/nearest-city", response_model=NearestCityRead | None)
def read_nearest_city(
    lat: float = Query(..., ge=-90, le=90, allow_inf_nan=False),
    lng: float = Query(..., ge=-180, le=180, allow_inf_nan=False),
    db: Session = Depends(get_db),
) -> NearestCityRead | None:
    _reject_null_island(lat, lng)
    row = nearest_city(db, lat, lng)
    return NearestCityRead.model_validate(row) if row else None


def _reject_null_island(lat: float, lng: float) -> None:
    if lat == 0 and lng == 0:
        raise HTTPException(status_code=422, detail="Координаты 0,0 не поддерживаются")
