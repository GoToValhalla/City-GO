"""Projection-only public catalog reads."""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.destination import Destination
from models.search_routing_stage5 import SearchPlaceDocument
from schemas.public_place import PublicPlaceRead
from services.projection_readiness_service import assert_projection_ready
from services.projection_observability import log_projection_read
from time import perf_counter

CATALOG_PROJECTION_TOGGLE = "catalog_projection_reads_enabled"


def list_catalog_places(
    db: Session, *, city_id: int | None = None, city_slug: str | None = None,
    destination_slug: str | None = None, category_id: int | None = None,
    tag_id: int | None = None, q: str | None = None, limit: int = 20,
    offset: int = 0, sort_by: str = "title", sort_order: str = "asc",
) -> tuple[list[PublicPlaceRead], int]:
    resolved_city = _city_id(db, city_id, city_slug)
    destination_id = _destination_id(db, destination_slug)
    if (city_slug and resolved_city is None) or (destination_slug and destination_id is None):
        return [], 0
    started = perf_counter()
    readiness = assert_projection_ready(db, projection_type="search_place_document", city_id=resolved_city)
    query = db.query(SearchPlaceDocument).filter(
        SearchPlaceDocument.is_public.is_(True),
        SearchPlaceDocument.is_catalog_visible.is_(True),
        SearchPlaceDocument.freshness_status == "fresh",
    )
    if resolved_city is not None:
        query = query.filter(SearchPlaceDocument.city_id == resolved_city)
    if q:
        needle = f"%{q.strip()}%"
        query = query.filter(or_(SearchPlaceDocument.title.ilike(needle), SearchPlaceDocument.searchable_text.ilike(needle)))
    docs = list(query.all())
    filtered = [row for row in docs if _matches(row, category_id, tag_id, destination_id)]
    ordered = sorted(filtered, key=_sort_key(sort_by), reverse=str(sort_order).lower() == "desc")
    result = [PublicPlaceRead(**row.public_payload) for row in ordered[offset:offset + limit]]
    log_projection_read(read_path="public_catalog", projection_type="search_place_document", city_id=resolved_city,
                        uses_projection=True, latency_ms=int((perf_counter() - started) * 1000),
                        source_version=readiness.source_version, projection_version=readiness.projection_version)
    return result, len(ordered)


def get_catalog_place(db: Session, *, place_id: int | None = None, slug: str | None = None) -> PublicPlaceRead | None:
    rows = db.query(SearchPlaceDocument).filter(
        SearchPlaceDocument.is_public.is_(True), SearchPlaceDocument.is_catalog_visible.is_(True),
        SearchPlaceDocument.freshness_status == "fresh",
    ).order_by(SearchPlaceDocument.source_snapshot_version.desc()).all()
    match = next((row for row in rows if place_id == row.place_id or slug == row.public_payload.get("slug")), None)
    if match is not None:
        assert_projection_ready(db, projection_type="search_place_document", city_id=int(match.city_id))
    else:
        assert_all_document_scopes(db, rows)
    return PublicPlaceRead(**match.public_payload) if match else None


def assert_all_document_scopes(db: Session, rows: list[SearchPlaceDocument]) -> None:
    city_ids = sorted({int(row.city_id) for row in rows})
    if not city_ids:
        assert_projection_ready(db, projection_type="search_place_document", city_id=None)
    for city_id in city_ids:
        assert_projection_ready(db, projection_type="search_place_document", city_id=city_id)


def _matches(row: SearchPlaceDocument, category_id: int | None, tag_id: int | None, destination_id: int | None) -> bool:
    metadata = row.tags_payload or {}
    return (
        (category_id is None or metadata.get("category_id") == category_id)
        and (tag_id is None or tag_id in metadata.get("tag_ids", []))
        and (destination_id is None or destination_id in metadata.get("destination_ids", []))
    )


def _sort_key(sort_by: str):
    return (lambda row: (-row.ranking_score, row.title or "", row.place_id)) if sort_by == "ranking_score" else (lambda row: (row.title or "", row.place_id))


def _city_id(db: Session, city_id: int | None, slug: str | None) -> int | None:
    if city_id is not None or slug is None:
        return city_id
    row = db.query(City).filter(City.slug == slug, City.is_active.is_(True), City.launch_status == "published").first()
    return int(row.id) if row else None


def _destination_id(db: Session, slug: str | None) -> int | None:
    if slug is None:
        return None
    row = db.query(Destination).filter(Destination.slug == slug, Destination.is_active.is_(True), Destination.is_published.is_(True)).first()
    return int(row.id) if row else None
