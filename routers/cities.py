"""
Список городов и чтение по id/slug.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.city import CityAvailableRead, CityRead
from services.city_service import city_is_published, get_available_cities, get_cities, get_city_by_id, get_city_by_slug

router = APIRouter(prefix="/cities", tags=["cities"])


# Возвращает список опубликованных городов из базы.
@router.get("/", response_model=list[CityRead])
def read_cities(db: Session = Depends(get_db)) -> list[CityRead]:
    return get_cities(db)


@router.get("/available", response_model=list[CityAvailableRead])
def read_available_cities(
    include_draft: bool = False,
    db: Session = Depends(get_db),
) -> list[CityAvailableRead]:
    return get_available_cities(db, include_draft=include_draft)


# Возвращает один опубликованный город по его slug.
@router.get("/by-slug/{slug}", response_model=CityRead)
def read_city_by_slug(slug: str, db: Session = Depends(get_db)) -> CityRead:
    city = get_city_by_slug(db, slug)
    if city is None or not city_is_published(city):
        raise HTTPException(status_code=404, detail="City not found")
    return city


# Возвращает один опубликованный город по его идентификатору.
@router.get("/{city_id}", response_model=CityRead)
def read_city(city_id: int, db: Session = Depends(get_db)) -> CityRead:
    city = get_city_by_id(db, city_id)
    if city is None or not city_is_published(city):
        raise HTTPException(status_code=404, detail="City not found")
    return city