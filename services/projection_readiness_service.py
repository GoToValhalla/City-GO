"""Fail-closed readiness for Stage 5 public projection generations."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.search_routing_stage5 import ProjectionRebuildJob
from services.public_read_projection_service import (
    PublicReadProjectionError, REASON_FAILED, REASON_INCOMPLETE,
    REASON_EMPTY, REASON_MISSING, REASON_RUNNING, REASON_STALE, REASON_VERSION,
)
from services.projection_snapshot_source import latest_published_snapshots, source_version
from services.projection_row_validation import assert_projection_rows

MAX_FRESHNESS_SECONDS = 24 * 60 * 60


@dataclass(frozen=True)
class ProjectionReadiness:
    projection_type: str
    city_id: int | None
    ready: bool
    reason: str
    source_version: int | None
    projection_version: int | None
    expected_count: int
    actual_count: int
    latest_job_id: int | None
    last_successful_job_id: int | None


def projection_readiness(db: Session, *, projection_type: str, city_id: int | None) -> ProjectionReadiness:
    base = db.query(ProjectionRebuildJob).filter(
        ProjectionRebuildJob.projection_type == projection_type,
    )
    query = base.filter(ProjectionRebuildJob.city_id.is_(None) if city_id is None else ProjectionRebuildJob.city_id == city_id)
    if city_id is not None and query.first() is None:
        query = base.filter(ProjectionRebuildJob.city_id.is_(None))
    latest = query.order_by(ProjectionRebuildJob.id.desc()).first()
    success = query.filter(ProjectionRebuildJob.status == "succeeded").order_by(ProjectionRebuildJob.id.desc()).first()
    snapshots = latest_published_snapshots(db, city_id=city_id)
    version = source_version(snapshots)
    compared_version = getattr(success, "source_snapshot_version", version) if city_id is not None and getattr(success, "city_id", city_id) is None else version
    reason = _reason(latest, success, compared_version)
    job = success or latest
    return ProjectionReadiness(
        projection_type, city_id, reason == "projection_ready", reason, version,
        getattr(job, "source_snapshot_version", None), len(snapshots),
        int(getattr(job, "actual_count", 0) or 0), getattr(latest, "id", None), getattr(success, "id", None),
    )


def assert_projection_ready(db: Session, *, projection_type: str, city_id: int | None) -> ProjectionReadiness:
    status = projection_readiness(db, projection_type=projection_type, city_id=city_id)
    if not status.ready:
        raise PublicReadProjectionError("Public read projection is unavailable", reason=status.reason)
    assert_projection_rows(db, status)
    return status


def readiness_payload(status: ProjectionReadiness) -> dict[str, object]:
    return asdict(status) | {"activation_safe": status.ready}


def _reason(latest: ProjectionRebuildJob | None, success: ProjectionRebuildJob | None, version: int | None) -> str:
    if latest is None:
        return REASON_EMPTY if version is not None else REASON_MISSING
    if latest.status in {"queued", "running"}:
        return REASON_RUNNING
    if latest.status == "failed":
        return REASON_FAILED
    if success is None or not success.is_complete or success.expected_count != success.actual_count:
        return REASON_INCOMPLETE
    if version is None or success.expected_count == 0:
        return REASON_EMPTY
    if success.source_snapshot_version != version:
        return REASON_VERSION
    finished = success.finished_at
    if finished is None or _age_seconds(finished) > MAX_FRESHNESS_SECONDS:
        return REASON_STALE
    return "projection_ready"


def _age_seconds(value: datetime) -> float:
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - aware).total_seconds()
