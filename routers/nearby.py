"""
Места в радиусе от переданных lat/lng (см. nearby_service).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.nearby import NearbyPlaceRead
from services.nearby_service import get_nearby_places

router = APIRouter(prefix="/nearby", tags=["nearby"])


# Возвращает список мест рядом с переданной точкой.
@router.get("/", response_model=list[NearbyPlaceRead])
def read_nearby_places(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(default=3.0),
    db: Session = Depends(get_db),
) -> list[NearbyPlaceRead]:
    return get_nearby_places(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )
