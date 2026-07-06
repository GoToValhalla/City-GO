"""Расширенный поиск и сортировка мест для операционной панели."""

from __future__ import annotations

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from models.place import Place
from services.admin_places_filters import apply_place_filters

_SORT_FIELDS = {
    "updated": Place.updated_at,
    "created": Place.created_at,
    "title": Place.title,
    "quality": Place.quality_score,
    "confidence": Place.existence_confidence_score,
    "id": Place.id,
}


def search_admin_places(
    db: Session,
    *,
    city_slug: str | None = None,
    destination_slug: str | None = None,
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
    sort: str = "updated",
    direction: str = "desc",
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Place], int]:
    query = apply_place_filters(
        db,
        db.query(Place),
        city_slug=city_slug,
        destination_slug=destination_slug,
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
    )
    total = query.count()
    column = _SORT_FIELDS.get(sort, Place.updated_at)
    ordering = asc(column) if direction == "asc" else desc(column)
    items = query.order_by(ordering, Place.id.desc()).offset(offset).limit(limit).all()
    return items, total
