"""
Подборки мест по городу (read).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.collection import CollectionRead
from services.collection_service import (
    get_collection_by_id,
    get_collection_by_slug,
    get_collections,
    get_collections_by_city_id,
)

router = APIRouter(prefix="/collections", tags=["collections"])


# Возвращает список всех подборок.
# Если передан city_id, возвращает подборки только выбранного города.
@router.get("/", response_model=list[CollectionRead])
def read_collections(
    city_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CollectionRead]:
    if city_id is not None:
        return get_collections_by_city_id(db, city_id)
    return get_collections(db)


# Возвращает одну подборку по идентификатору.
@router.get("/{collection_id}", response_model=CollectionRead)
def read_collection(collection_id: int, db: Session = Depends(get_db)) -> CollectionRead:
    collection = get_collection_by_id(db, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


# Возвращает одну подборку по slug.
@router.get("/by-slug/{slug}", response_model=CollectionRead)
def read_collection_by_slug(slug: str, db: Session = Depends(get_db)) -> CollectionRead:
    collection = get_collection_by_slug(db, slug)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
