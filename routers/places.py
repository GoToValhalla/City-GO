"""
HTTP-слой публичного чтения мест. Привилегированные записи — только /admin/places.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.public_place import PublicPlaceRead, PublicPlaceSearchResponse
from services.place_read_service import build_public_place_read, build_public_place_reads
from services.place_service import (
    get_place_by_id,
    get_place_by_slug,
    get_places,
    get_places_total,
)
from services.catalog_projection_read_service import CATALOG_PROJECTION_TOGGLE, get_catalog_place, list_catalog_places
from services.feature_toggle_service import is_toggle_enabled
from services.projection_http_error import raise_projection_unavailable
from services.public_read_projection_service import PublicReadProjectionError
from services.projection_observability import log_projection_read
from time import perf_counter

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
    started = perf_counter()
    if city_slug and destination_slug:
        raise HTTPException(status_code=400, detail="Use either city_slug or destination_slug, not both")
    projection_enabled = is_toggle_enabled(db, CATALOG_PROJECTION_TOGGLE, default=False)
    try:
        if projection_enabled:
            projected, total = list_catalog_places(
                db, city_id=city_id, city_slug=city_slug, destination_slug=destination_slug,
                category_id=category_id, tag_id=tag_id, q=q, limit=limit, offset=offset,
                sort_by=sort_by, sort_order=sort_order,
            )
            return PublicPlaceSearchResponse(items=projected, total=total, limit=limit, offset=offset)
    except PublicReadProjectionError as exc:
        raise_projection_unavailable(exc, read_path="public_catalog")
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
    log_projection_read(read_path="public_catalog", projection_type="search_place_document", city_id=city_id,
                        uses_projection=False, latency_ms=int((perf_counter() - started) * 1000))

    return PublicPlaceSearchResponse(
        items=build_public_place_reads(db, items),
        total=total,
        limit=limit,
        offset=offset,
    )


# Возвращает одно место по его идентификатору.
@router.get("/{place_id}", response_model=PublicPlaceRead, response_model_exclude_none=True)
def read_place(place_id: int, db: Session = Depends(get_db)) -> PublicPlaceRead:
    if is_toggle_enabled(db, CATALOG_PROJECTION_TOGGLE, default=False):
        try:
            projected = get_catalog_place(db, place_id=place_id)
        except PublicReadProjectionError as exc:
            raise_projection_unavailable(exc, read_path="public_catalog")
        if projected is None:
            raise HTTPException(status_code=404, detail="Place not found")
        return projected
    place = get_place_by_id(db, place_id, public_only=True)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return build_public_place_read(db, place)


# Возвращает одно место по его slug.
@router.get("/by-slug/{slug}", response_model=PublicPlaceRead, response_model_exclude_none=True)
def read_place_by_slug(slug: str, db: Session = Depends(get_db)) -> PublicPlaceRead:
    if is_toggle_enabled(db, CATALOG_PROJECTION_TOGGLE, default=False):
        try:
            projected = get_catalog_place(db, slug=slug)
        except PublicReadProjectionError as exc:
            raise_projection_unavailable(exc, read_path="public_catalog")
        if projected is None:
            raise HTTPException(status_code=404, detail="Place not found")
        return projected
    place = get_place_by_slug(db, slug, public_only=True)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return build_public_place_read(db, place)
