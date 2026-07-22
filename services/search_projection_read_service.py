"""Live public search against SearchPlaceDocument when Stage 5 toggle is ON."""

from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.search_routing_stage5 import SearchPlaceDocument
from services.place_public_visibility import apply_public_place_visibility
from services.public_read_projection_service import FRESH_STATUS, PublicReadProjectionError
from services.search_projection_readiness import assert_search_projection_ready

SEARCH_PROJECTION_TOGGLE = "search_projection_reads_enabled"


def raise_projection_http_error(exc: PublicReadProjectionError) -> NoReturn:
    raise HTTPException(
        status_code=503,
        detail={
            "code": "public_read_projection_unavailable",
            "reason": exc.reason,
            "read_path": "search",
            "message": str(exc),
        },
    ) from exc


def search_public_places_via_projection(
    db: Session,
    *,
    q: str,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    sort_order: str = "asc",
) -> tuple[list[Place], int]:
    resolved_city_id = _resolve_city_id(db, city_id=city_id, city_slug=city_slug)
    if city_slug is not None and resolved_city_id is None and city_id is None:
        return [], 0
    assert_search_projection_ready(db, city_id=resolved_city_id)
    docs = _matching_search_docs(
        db, q=q, city_id=resolved_city_id, sort_by=sort_by, sort_order=sort_order
    )
    places = _load_visible_places(
        db, [int(doc.place_id) for doc in docs], category_id=category_id, tag_id=tag_id
    )
    return places[offset : offset + limit], len(places)


def _matching_search_docs(db, *, q, city_id, sort_by, sort_order) -> list[SearchPlaceDocument]:
    needle = f"%{q.strip()}%"
    query = db.query(SearchPlaceDocument).filter(
        SearchPlaceDocument.is_public.is_(True),
        SearchPlaceDocument.is_search_visible.is_(True),
        SearchPlaceDocument.freshness_status == FRESH_STATUS,
        or_(SearchPlaceDocument.title.ilike(needle), SearchPlaceDocument.searchable_text.ilike(needle)),
    )
    if city_id is not None:
        query = query.filter(SearchPlaceDocument.city_id == city_id)
    column = SearchPlaceDocument.ranking_score if sort_by == "ranking_score" else SearchPlaceDocument.title
    ordered = column.desc() if str(sort_order).lower() == "desc" else column.asc()
    return list(query.order_by(ordered).all())


def _load_visible_places(db, place_ids, *, category_id, tag_id) -> list[Place]:
    if not place_ids:
        return []
    query = apply_public_place_visibility(db.query(Place).filter(Place.id.in_(place_ids)))
    if category_id is not None:
        query = query.filter(Place.category_id == category_id)
    if tag_id is not None:
        from models.place_tag import PlaceTag

        query = query.join(PlaceTag, Place.id == PlaceTag.place_id).filter(PlaceTag.tag_id == tag_id)
    by_id = {int(place.id): place for place in query.all()}
    return [by_id[place_id] for place_id in place_ids if place_id in by_id]


def _resolve_city_id(db: Session, *, city_id: int | None, city_slug: str | None) -> int | None:
    if city_id is not None:
        return city_id
    if city_slug is None:
        return None
    city = db.query(City).filter(
        City.slug == city_slug, City.is_active.is_(True), City.launch_status == "published"
    ).first()
    return int(city.id) if city is not None else None
