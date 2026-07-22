"""Search projection readiness against PublishedPlaceSnapshot + SearchPlaceDocument."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.search_routing_stage5 import SearchPlaceDocument
from services.public_read_projection_service import (
    FRESH_STATUS,
    PublicReadProjectionError,
    REASON_EMPTY,
    REASON_STALE,
    REASON_VERSION,
)
from services.projection_readiness_service import assert_projection_ready
from services.projection_snapshot_source import latest_published_snapshots


def assert_search_projection_ready(db: Session, *, city_id: int | None):
    status = assert_projection_ready(db, projection_type="search_place_document", city_id=city_id)
    snapshots = latest_search_snapshots(db, city_id=city_id)
    if not snapshots:
        return status
    docs_by_place = docs_by_place_id(db, city_id=city_id)
    if not docs_by_place:
        raise PublicReadProjectionError(
            "Public read projection is empty",
            reason=REASON_EMPTY,
        )
    matched_versions: list[int] = []
    for snapshot in snapshots:
        doc = docs_by_place.get(int(snapshot.place_id))
        if doc is None or int(doc.source_snapshot_version) != int(snapshot.snapshot_version):
            raise PublicReadProjectionError(
                "Search projection is version-incompatible with published snapshots",
                reason=REASON_VERSION,
            )
        if doc.freshness_status != FRESH_STATUS:
            raise PublicReadProjectionError(
                "Public read projection is stale",
                reason=REASON_STALE,
            )
        matched_versions.append(int(doc.source_snapshot_version))
    if len(matched_versions) != len(snapshots) or status.actual_count < len(snapshots):
        raise PublicReadProjectionError("Search projection is incomplete", reason="projection_incomplete")
    return status


def latest_search_snapshots(db: Session, *, city_id: int | None):
    return [row for row in latest_published_snapshots(db, city_id=city_id) if row.is_search_visible]


def docs_by_place_id(db: Session, *, city_id: int | None) -> dict[int, SearchPlaceDocument]:
    query = db.query(SearchPlaceDocument).filter(
        SearchPlaceDocument.is_public.is_(True),
        SearchPlaceDocument.is_search_visible.is_(True),
    )
    if city_id is not None:
        query = query.filter(SearchPlaceDocument.city_id == city_id)
    rows = list(query.order_by(SearchPlaceDocument.source_snapshot_version.desc()).all())
    by_place: dict[int, SearchPlaceDocument] = {}
    for row in rows:
        place_id = int(row.place_id)
        if place_id not in by_place:
            by_place[place_id] = row
    return by_place
