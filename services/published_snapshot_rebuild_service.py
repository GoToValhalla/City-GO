"""Rebuild immutable Stage 5 source snapshots from canonical Place state."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.place import Place
from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import ProjectionRebuildJob
from services.data_foundation_projection_service import build_snapshot_from_place
from services.projection_rebuild_lock import serialize_projection_rebuilds


def rebuild_published_place_snapshots(
    db: Session, *, city_id: int | None = None, actor: str = "system",
    source: str = "projection_rebuild", audit_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Append one current-state snapshot per place; never mutate Place."""

    serialize_projection_rebuilds(db)
    query = db.query(Place)
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)
    places = query.order_by(Place.id.asc()).all()
    version = int(db.query(func.max(PublishedPlaceSnapshot.snapshot_version)).scalar() or 0) + 1
    now = datetime.now(timezone.utc)
    job = ProjectionRebuildJob(
        projection_type="published_place_snapshot", city_id=city_id, status="running",
        scope_key="global" if city_id is None else f"city:{city_id}", generation=uuid4().hex,
        source_snapshot_version=version, expected_count=len(places), actor=actor, source=source,
        audit_context=audit_context or {}, started_at=now,
    )
    db.add(job)
    db.flush()
    db.add_all(list(map(lambda place: build_snapshot_from_place(place, snapshot_version=version), places)))
    db.flush()
    job.status = "succeeded"
    job.processed_count = len(places)
    job.rebuilt_count = len(places)
    job.actual_count = len(places)
    job.is_complete = True
    job.finished_at = datetime.now(timezone.utc)
    db.flush()
    return {
        "job_id": job.id, "projection_type": job.projection_type, "status": job.status,
        "source_snapshot_version": version, "processed_count": len(places),
        "rebuilt_count": len(places), "expected_count": len(places), "actual_count": len(places),
        "generation": job.generation, "is_complete": True,
    }
