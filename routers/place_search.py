"""
Поиск мест с обязательным query-параметром `q`.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.public_place import PublicPlaceSearchResponse
from services.feature_toggle_service import is_toggle_enabled
from services.place_read_service import build_public_place_reads
from services.place_service import get_places, get_places_total
from services.public_read_projection_service import PublicReadProjectionError
from services.search_projection_read_service import (
    SEARCH_PROJECTION_TOGGLE,
    raise_projection_http_error,
    search_public_places_via_projection,
)

router = APIRouter(prefix="/places/search", tags=["place-search"])


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
    if is_toggle_enabled(db, SEARCH_PROJECTION_TOGGLE, default=False):
        try:
            items, total = search_public_places_via_projection(
                db,
                q=q,
                city_id=city_id,
                city_slug=city_slug,
                category_id=category_id,
                tag_id=tag_id,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except PublicReadProjectionError as exc:
            raise_projection_http_error(exc)
    else:
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
