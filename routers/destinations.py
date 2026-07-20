"""Public Destination API v1."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.destination import DestinationCenter, DestinationDetail, DestinationListItem, DestinationListResponse, DestinationScopeSummary
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_service import (
    count_places_for_destination,
    count_published_destinations,
    has_children,
    list_children,
    list_published_destinations,
    list_scopes,
)

router = APIRouter(prefix="/v1/destinations", tags=["destinations"])


def _to_list_item(db: Session, row) -> DestinationListItem:
    return DestinationListItem(
        id=row.id,
        slug=row.slug,
        title=row.name,
        destination_type=row.destination_type,
        parent_id=row.parent_id,
        center=DestinationCenter(lat=row.center_lat, lng=row.center_lng),
        readiness_score=row.readiness_score,
        has_children=has_children(db, row.id),
        places_count=count_places_for_destination(db, row.id),
    )


@router.get("", response_model=DestinationListResponse)
def read_destinations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DestinationListResponse:
    items = [_to_list_item(db, row) for row in list_published_destinations(db, limit=limit, offset=offset)]
    return DestinationListResponse(items=items, total=count_published_destinations(db))


@router.get("/{slug}", response_model=DestinationDetail)
def read_destination(slug: str, db: Session = Depends(get_db)) -> DestinationDetail:
    row = get_destination_by_slug(db, slug)
    if row is None or not row.is_active or not row.is_published:
        raise HTTPException(status_code=404, detail="Destination not found")
    base = _to_list_item(db, row)
    children = [_to_list_item(db, child) for child in list_children(db, row.id)]
    scopes = [
        DestinationScopeSummary.model_validate(scope)
        for scope in list_scopes(db, row.id)
    ]
    return DestinationDetail(
        **base.model_dump(),
        launch_status=row.launch_status,
        is_published=row.is_published,
        sub_destinations=children,
        scopes=scopes,
    )
