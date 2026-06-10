"""
Точки внутри подборки (порядок мест в collection).
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.collection_place import CollectionPlaceRead
from services.collection_place_service import (
    get_collection_places,
    get_collection_places_by_collection_id,
)

router = APIRouter(prefix="/collection-places", tags=["collection-places"])


# Возвращает список всех связей подборок и мест.
# Если передан collection_id, возвращает связи только для выбранной подборки.
@router.get("/", response_model=list[CollectionPlaceRead])
def read_collection_places(
    collection_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CollectionPlaceRead]:
    if collection_id is not None:
        return get_collection_places_by_collection_id(db, collection_id)
    return get_collection_places(db)
