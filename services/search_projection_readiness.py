"""Search projection readiness against PublishedPlaceSnapshot + SearchPlaceDocument."""

from __future__ import annotations

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import SearchPlaceDocument
from services.public_read_projection_service import (
    FRESH_STATUS,
    PublicReadProjectionError,
    REASON_EMPTY,
    REASON_MISSING,
    REASON_STALE,
    REASON_VERSION,
    choose_public_read_path,
)


def assert_search_projection_ready(db: Session, *, city_id: int | None) -> None:
    snapshots = latest_search_snapshots(db, city_id=city_id)
    if not snapshots:
        raise PublicReadProjectionError(
            "Authoritative published search snapshots are missing",
            reason=REASON_MISSING,
        )
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
    source_version = max(int(row.snapshot_version) for row in snapshots)
    choose_public_read_path(
        read_path="search",
        projection_type="search_place_document",
        projection_count=len(matched_versions),
        source_snapshot_version=source_version,
        projection_snapshot_version=max(matched_versions),
        freshness_status=FRESH_STATUS,
        fallback_allowed=False,
    )


def latest_search_snapshots(db: Session, *, city_id: int | None) -> list[PublishedPlaceSnapshot]:
    query = db.query(
        PublishedPlaceSnapshot.place_id,
        func.max(PublishedPlaceSnapshot.snapshot_version).label("max_version"),
    ).filter(
        PublishedPlaceSnapshot.is_public.is_(True),
        PublishedPlaceSnapshot.is_search_visible.is_(True),
    )
    if city_id is not None:
        query = query.filter(PublishedPlaceSnapshot.city_id == city_id)
    latest = query.group_by(PublishedPlaceSnapshot.place_id).subquery()
    return list(
        db.query(PublishedPlaceSnapshot)
        .join(
            latest,
            and_(
                PublishedPlaceSnapshot.place_id == latest.c.place_id,
                PublishedPlaceSnapshot.snapshot_version == latest.c.max_version,
            ),
        )
        .all()
    )


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
