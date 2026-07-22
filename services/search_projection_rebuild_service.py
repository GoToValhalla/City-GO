"""Rebuild SearchPlaceDocument rows from PublishedPlaceSnapshot only."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from models.search_routing_stage5 import ProjectionRebuildJob, SearchPlaceDocument
from services.public_read_projection_service import build_projection_rebuild_summary
from services.projection_snapshot_source import latest_published_snapshots, source_version
from services.projection_rebuild_lock import serialize_projection_rebuilds
from services.search_projection_builder import document_payload, valid_public_payload


def rebuild_search_place_documents(
    db: Session, *, city_id: int | None = None, locale: str = "default",
    actor: str = "system", source: str = "projection_rebuild", audit_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Derive search projections from latest public snapshots; never mutates Place."""

    serialize_projection_rebuilds(db)
    running = db.query(ProjectionRebuildJob).filter(
        ProjectionRebuildJob.projection_type == "search_place_document",
        ProjectionRebuildJob.city_id.is_(None) if city_id is None else ProjectionRebuildJob.city_id == city_id,
        ProjectionRebuildJob.status.in_(("queued", "running")),
    ).first()
    if running is not None:
        return _job_summary(running, status="skipped")
    snapshots = latest_published_snapshots(db, city_id=city_id)
    now = datetime.now(timezone.utc)
    job = ProjectionRebuildJob(
        projection_type="search_place_document",
        city_id=city_id,
        status="running",
        scope_key="global" if city_id is None else f"city:{city_id}",
        generation=uuid4().hex,
        source_snapshot_version=source_version(snapshots),
        expected_count=len(snapshots),
        actor=actor,
        source=source,
        audit_context=audit_context or {},
        started_at=now,
    )
    db.add(job)
    db.flush()
    if any(not valid_public_payload(row) for row in snapshots):
        job.status = "failed"
        job.failed_count = 1
        job.error_summary = "projection_source_payload_incompatible"
        job.finished_at = datetime.now(timezone.utc)
        db.flush()
        return _job_summary(job, status="failed")
    target = db.query(SearchPlaceDocument).filter(SearchPlaceDocument.locale == locale)
    if city_id is not None:
        target = target.filter(SearchPlaceDocument.city_id == city_id)
    target.delete(synchronize_session=False)
    db.add_all([SearchPlaceDocument(**document_payload(row, locale=locale)) for row in snapshots])
    versions = [int(row.snapshot_version) for row in snapshots]
    summary = build_projection_rebuild_summary(
        projection_type="search_place_document",
        source_snapshot_version=max(versions) if versions else None,
        processed_count=len(snapshots),
        rebuilt_count=len(snapshots),
    )
    summary["job_id"] = job.id
    job.status = str(summary["status"])
    job.source_snapshot_version = summary["source_snapshot_version"]  # type: ignore[assignment]
    job.processed_count = int(summary["processed_count"])
    job.rebuilt_count = int(summary["rebuilt_count"])
    job.actual_count = len(snapshots)
    job.is_complete = True
    job.finished_at = datetime.now(timezone.utc)
    db.flush()
    return summary


def _job_summary(job: ProjectionRebuildJob, *, status: str) -> dict[str, object]:
    return {"job_id": job.id, "projection_type": job.projection_type, "status": status,
            "source_snapshot_version": job.source_snapshot_version, "processed_count": 0,
            "rebuilt_count": job.rebuilt_count, "skipped_count": 1 if status == "skipped" else 0,
            "failed_count": job.failed_count, "error_summary": job.error_summary}
