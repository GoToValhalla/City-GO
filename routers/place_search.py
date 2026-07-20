"""
Поиск мест с обязательным query-параметром `q`.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.public_place import PublicPlaceSearchResponse
from services.place_read_service import build_public_place_reads
from services.place_service import get_places, get_places_total

router = APIRouter(prefix="/places/search", tags=["place-search"])


# Возвращает список мест по текстовому запросу и дополнительным фильтрам.
@router.get("/", response_model=PublicPlaceSearchResponse)
def search_places(
    q: str = Query(...),
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="title"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PublicPlaceSearchResponse:
    items = get_places(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
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
