"""Rebuild SearchPlaceDocument rows from PublishedPlaceSnapshot only."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import ProjectionRebuildJob, SearchPlaceDocument
from services.public_read_projection_service import (
    build_projection_rebuild_summary,
    build_search_document_from_snapshot,
)


def rebuild_search_place_documents(
    db: Session, *, city_id: int | None = None, locale: str = "default"
) -> dict[str, object]:
    """Derive search projections from latest public snapshots; never mutates Place."""

    snapshots = _latest_public_snapshots(db, city_id=city_id)
    job = ProjectionRebuildJob(
        projection_type="search_place_document",
        city_id=city_id,
        status="running",
        started_at=datetime.utcnow(),
    )
    db.add(job)
    db.flush()
    place_ids = [int(row.place_id) for row in snapshots]
    if place_ids:
        (
            db.query(SearchPlaceDocument)
            .filter(
                SearchPlaceDocument.place_id.in_(place_ids),
                SearchPlaceDocument.locale == locale,
            )
            .delete(synchronize_session=False)
        )
    for snapshot in snapshots:
        db.add(SearchPlaceDocument(**_document_payload(snapshot, locale=locale)))
    versions = [int(row.snapshot_version) for row in snapshots]
    summary = build_projection_rebuild_summary(
        projection_type="search_place_document",
        source_snapshot_version=max(versions) if versions else None,
        processed_count=len(snapshots),
        rebuilt_count=len(snapshots),
    )
    job.status = str(summary["status"])
    job.source_snapshot_version = summary["source_snapshot_version"]  # type: ignore[assignment]
    job.processed_count = int(summary["processed_count"])
    job.rebuilt_count = int(summary["rebuilt_count"])
    job.finished_at = datetime.utcnow()
    db.flush()
    return summary


def _latest_public_snapshots(db: Session, *, city_id: int | None) -> list[PublishedPlaceSnapshot]:
    query = db.query(
        PublishedPlaceSnapshot.place_id,
        func.max(PublishedPlaceSnapshot.snapshot_version).label("max_version"),
    ).filter(PublishedPlaceSnapshot.is_public.is_(True))
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


def _document_payload(snapshot: PublishedPlaceSnapshot, *, locale: str) -> dict[str, object]:
    payload = snapshot.snapshot_payload or {}
    quality = snapshot.quality_payload or {}
    return build_search_document_from_snapshot(
        snapshot={
            "place_id": snapshot.place_id,
            "city_id": snapshot.city_id,
            "snapshot_version": snapshot.snapshot_version,
            "title": snapshot.title,
            "description": payload.get("short_description"),
            "category": payload.get("canonical_category") or payload.get("category"),
            "tags": payload.get("tags") or [],
            "is_public": snapshot.is_public,
            "is_search_visible": snapshot.is_search_visible,
            "ranking_score": quality.get("quality_score", 0),
        },
        locale=locale,
    )
