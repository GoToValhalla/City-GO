from __future__ import annotations

from sqlalchemy.orm import Session

from models.search_routing_stage5 import ProjectionRebuildJob
from schemas.projection_operations import ProjectionRebuildRequest
from services.feature_toggle_service import is_toggle_enabled
from services.projection_activation_service import TOGGLE_PROJECTIONS, assert_toggle_activation_safe
from services.projection_observability import log_rebuild_result
from services.projection_readiness_service import projection_readiness, readiness_payload
from services.public_read_projection_service import PublicReadProjectionError
from services.stage6_contracts.projection import ProjectionRebuildCommand, rebuild_projection


class ProjectionRebuildFailed(RuntimeError):
    pass


def rebuild(db: Session, payload: ProjectionRebuildRequest, *, actor: str, kind: str) -> dict[str, object]:
    command = ProjectionRebuildCommand(kind, payload.city_id, actor, payload.source, payload.audit_context)
    try:
        result = rebuild_projection(db, command)
        db.commit()
    except (ValueError, LookupError):
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        _record_failure(db, kind, payload, actor, exc)
        raise ProjectionRebuildFailed from exc
    log_rebuild_result(
        projection_type=kind, city_id=payload.city_id, status=str(result["status"]),
        reason=str(result.get("error_summary") or "") or None,
    )
    return result


def readiness(db: Session, *, kind: str, city_id: int | None) -> dict[str, object]:
    payload = readiness_payload(projection_readiness(db, projection_type=kind, city_id=city_id))
    jobs = db.query(ProjectionRebuildJob).filter(
        ProjectionRebuildJob.projection_type == kind,
        ProjectionRebuildJob.city_id.is_(None) if city_id is None else ProjectionRebuildJob.city_id == city_id,
    )
    latest = jobs.order_by(ProjectionRebuildJob.id.desc()).first()
    success = jobs.filter(ProjectionRebuildJob.status == "succeeded").order_by(ProjectionRebuildJob.id.desc()).first()
    failure = jobs.filter(ProjectionRebuildJob.status == "failed").order_by(ProjectionRebuildJob.id.desc()).first()
    payload.update({
        "latest_rebuild_job": _job_payload(latest),
        "last_successful_rebuild": _job_payload(success),
        "last_failure_reason": getattr(failure, "error_summary", None),
        "active_toggles": {
            key: is_toggle_enabled(db, key, default=False)
            for key, kinds in TOGGLE_PROJECTIONS.items() if kind in kinds
        },
    })
    return payload


def activation_safety(db: Session, toggle_key: str) -> dict[str, object]:
    active = is_toggle_enabled(db, toggle_key, default=False)
    try:
        assert_toggle_activation_safe(db, toggle_key)
    except PublicReadProjectionError as exc:
        return {"toggle_key": toggle_key, "active": active, "activation_safe": False, "reason": exc.reason}
    return {"toggle_key": toggle_key, "active": active, "activation_safe": True, "reason": "projection_ready"}


def job_payload(db: Session, job_id: int) -> dict[str, object] | None:
    return _job_payload(db.query(ProjectionRebuildJob).filter(ProjectionRebuildJob.id == job_id).first())


def _record_failure(db: Session, kind: str, payload: ProjectionRebuildRequest, actor: str, exc: Exception) -> None:
    row = ProjectionRebuildJob(
        projection_type=kind, city_id=payload.city_id,
        scope_key="global" if payload.city_id is None else f"city:{payload.city_id}",
        status="failed", actor=actor, source=payload.source, audit_context=payload.audit_context,
        failed_count=1, error_summary=type(exc).__name__,
    )
    db.add(row); db.commit()
    log_rebuild_result(projection_type=kind, city_id=payload.city_id, status="failed", reason=type(exc).__name__)


def _job_payload(row: ProjectionRebuildJob | None) -> dict[str, object] | None:
    return None if row is None else {column.name: getattr(row, column.name) for column in row.__table__.columns}
