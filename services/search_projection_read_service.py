"""Live public search against SearchPlaceDocument when Stage 5 toggle is ON."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.search_routing_stage5 import SearchPlaceDocument
from schemas.public_place import PublicPlaceRead
from services.public_read_projection_service import FRESH_STATUS
from services.search_projection_readiness import assert_search_projection_ready
from services.projection_observability import log_projection_read
from time import perf_counter

SEARCH_PROJECTION_TOGGLE = "search_projection_reads_enabled"


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
) -> tuple[list[PublicPlaceRead], int]:
    resolved_city_id = _resolve_city_id(db, city_id=city_id, city_slug=city_slug)
    if city_slug is not None and resolved_city_id is None and city_id is None:
        return [], 0
    started = perf_counter()
    readiness = assert_search_projection_ready(db, city_id=resolved_city_id)
    docs = _matching_search_docs(
        db, q=q, city_id=resolved_city_id, sort_by=sort_by, sort_order=sort_order
    )
    filtered = [doc for doc in docs if _matches_projection_filters(doc, category_id, tag_id)]
    items = [PublicPlaceRead(**doc.public_payload) for doc in filtered]
    log_projection_read(read_path="search", projection_type="search_place_document", city_id=resolved_city_id,
                        uses_projection=True, latency_ms=int((perf_counter() - started) * 1000),
                        source_version=readiness.source_version, projection_version=readiness.projection_version)
    return items[offset : offset + limit], len(items)


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


def _matches_projection_filters(doc: SearchPlaceDocument, category_id: int | None, tag_id: int | None) -> bool:
    metadata = doc.tags_payload or {}
    category_matches = category_id is None or metadata.get("category_id") == category_id
    tag_ids = metadata.get("tag_ids", [])
    return category_matches and (tag_id is None or tag_id in tag_ids)


def _resolve_city_id(db: Session, *, city_id: int | None, city_slug: str | None) -> int | None:
    if city_id is not None:
        return city_id
    if city_slug is None:
        return None
    city = db.query(City).filter(
        City.slug == city_slug, City.is_active.is_(True), City.launch_status == "published"
    ).first()
    return int(city.id) if city is not None else None
