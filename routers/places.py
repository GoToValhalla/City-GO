"""
HTTP-слой CRUD и списка мест: делегирует в services.place_service.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place import PlaceCreate, PlaceRead, PlaceUpdate
from schemas.public_place import PublicPlaceRead, PublicPlaceSearchResponse
from services.place_read_service import build_place_read, build_public_place_read, build_public_place_reads
from services.place_service import (
    create_place,
    delete_place,
    get_place_by_id,
    get_place_by_slug,
    get_places,
    get_places_total,
    update_place,
)

router = APIRouter(prefix="/places", tags=["places"])


# Возвращает список мест из базы с учетом фильтров.
@router.get("/", response_model=PublicPlaceSearchResponse)
def read_places(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    destination_slug: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="title"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PublicPlaceSearchResponse:
    if city_slug and destination_slug:
        raise HTTPException(status_code=400, detail="Use either city_slug or destination_slug, not both")
    items = get_places(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        destination_slug=destination_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total = get_places_total(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        destination_slug=destination_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
    )

    return PublicPlaceSearchResponse(
        items=build_public_place_reads(db, items),
        total=total,
        limit=limit,
        offset=offset,
    )


# Возвращает одно место по его идентификатору.
@router.get("/{place_id}", response_model=PublicPlaceRead, response_model_exclude_none=True)
def read_place(place_id: int, db: Session = Depends(get_db)) -> PublicPlaceRead:
    place = get_place_by_id(db, place_id, public_only=True)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return build_public_place_read(db, place)


# Возвращает одно место по его slug.
@router.get("/by-slug/{slug}", response_model=PublicPlaceRead, response_model_exclude_none=True)
def read_place_by_slug(slug: str, db: Session = Depends(get_db)) -> PublicPlaceRead:
    place = get_place_by_slug(db, slug, public_only=True)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return build_public_place_read(db, place)


# Создает новое место в базе.
@router.post("/", response_model=PlaceRead)
def create_new_place(
    place_in: PlaceCreate,
    db: Session = Depends(get_db),
) -> PlaceRead:
    return build_place_read(db, create_place(db, place_in))


# Обновляет существующее место по идентификатору.
@router.put("/{place_id}", response_model=PlaceRead)
def update_existing_place(
    place_id: int,
    place_in: PlaceUpdate,
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = update_place(db, place_id, place_in)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return build_place_read(db, place)


# Удаляет место по идентификатору.
@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_place(place_id: int, db: Session = Depends(get_db)) -> None:
    deleted = delete_place(db, place_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Place not found")
