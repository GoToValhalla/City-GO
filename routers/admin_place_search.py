"""Расширенный фильтруемый список мест для операционной панели."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin import AdminPlaceListResponse
from services.admin_place_search_service import search_admin_places
from services.place_read_service import build_place_reads

router = APIRouter(prefix="/admin", tags=["admin-place-search"])


@router.get("/places/search", response_model=AdminPlaceListResponse)
def search_places(
    city_slug: str | None = None,
    publication_status: str | None = None,
    verification_status: str | None = None,
    category: str | None = None,
    q: str | None = None,
    preset: str | None = None,
    has_photo: bool | None = None,
    has_address: bool | None = None,
    has_description: bool | None = None,
    has_phone: bool | None = None,
    has_website: bool | None = None,
    has_opening_hours: bool | None = None,
    route_eligible: bool | None = None,
    is_active: bool | None = None,
    searchable: bool | None = None,
    low_confidence: bool | None = None,
    quality_tier: str | None = None,
    source: str | None = None,
    reason: str | None = None,
    sort: str = Query(default="updated", pattern="^(updated|created|title|quality|confidence|id)$"),
    direction: str = Query(default="desc", pattern="^(asc|desc)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceListResponse:
    items, total = search_admin_places(
        db,
        city_slug=city_slug,
        publication_status=publication_status,
        verification_status=verification_status,
        category=category,
        q=q,
        preset=preset,
        has_photo=has_photo,
        has_address=has_address,
        has_description=has_description,
        has_phone=has_phone,
        has_website=has_website,
        has_opening_hours=has_opening_hours,
        route_eligible=route_eligible,
        is_active=is_active,
        searchable=searchable,
        low_confidence=low_confidence,
        quality_tier=quality_tier,
        source=source,
        reason=reason,
        sort=sort,
        direction=direction,
        limit=limit,
        offset=offset,
    )
    return AdminPlaceListResponse(items=build_place_reads(db, items), total=total, limit=limit, offset=offset)
