"""Authenticated Stage 5 rebuild, readiness, and rollout controls."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.search_routing_stage5 import ProjectionRebuildJob
from schemas.projection_operations import ProjectionReadinessResponse, ProjectionRebuildRequest
from services.projection_readiness_service import projection_readiness, readiness_payload
from services.public_read_projection_service import PublicReadProjectionError
from services.routing_projection_rebuild_service import rebuild_route_candidate_sets, rebuild_routing_place_nodes
from services.search_projection_rebuild_service import rebuild_search_place_documents
from services.projection_observability import log_rebuild_result
from services.feature_toggle_service import is_toggle_enabled
from services.projection_activation_service import TOGGLE_PROJECTIONS, assert_toggle_activation_safe
from services.published_snapshot_rebuild_service import rebuild_published_place_snapshots

router = APIRouter(prefix="/admin/projections", tags=["admin-projections"])
KINDS = {"snapshot": "published_place_snapshot", "search": "search_place_document", "catalog": "search_place_document", "routing": "routing_place_node", "route_candidate_set": "route_candidate_set"}


@router.post("/rebuild")
def start_rebuild(payload: ProjectionRebuildRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    kind = KINDS.get(payload.projection_type, payload.projection_type)
    try:
        result = _run(db, kind, payload, auth.actor_id)
        db.commit()
        log_rebuild_result(projection_type=kind, city_id=payload.city_id, status=str(result["status"]), reason=str(result.get("error_summary") or "") or None)
        return result
    except (ValueError, PublicReadProjectionError) as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        _record_failure(db, kind, payload, auth.actor_id, exc)
        raise HTTPException(status_code=500, detail="Projection rebuild failed") from exc


@router.get("/readiness", response_model=ProjectionReadinessResponse)
def read_readiness(projection_type: str = Query(...), city_id: int | None = Query(default=None), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ProjectionReadinessResponse:
    kind = KINDS.get(projection_type, projection_type)
    payload = readiness_payload(projection_readiness(db, projection_type=kind, city_id=city_id))
    jobs = db.query(ProjectionRebuildJob).filter(ProjectionRebuildJob.projection_type == kind,
        ProjectionRebuildJob.city_id.is_(None) if city_id is None else ProjectionRebuildJob.city_id == city_id)
    latest = jobs.order_by(ProjectionRebuildJob.id.desc()).first()
    success = jobs.filter(ProjectionRebuildJob.status == "succeeded").order_by(ProjectionRebuildJob.id.desc()).first()
    failure = jobs.filter(ProjectionRebuildJob.status == "failed").order_by(ProjectionRebuildJob.id.desc()).first()
    payload.update({"latest_rebuild_job": _job_payload(latest), "last_successful_rebuild": _job_payload(success),
                    "last_failure_reason": getattr(failure, "error_summary", None),
                    "active_toggles": {key: is_toggle_enabled(db, key, default=False) for key, kinds in TOGGLE_PROJECTIONS.items() if kind in kinds}})
    return ProjectionReadinessResponse(**payload)


@router.get("/activation-safety")
def read_activation_safety(toggle_key: str = Query(...), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if toggle_key not in TOGGLE_PROJECTIONS:
        raise HTTPException(status_code=422, detail="Unsupported projection toggle")
    try:
        assert_toggle_activation_safe(db, toggle_key)
    except PublicReadProjectionError as exc:
        return {"toggle_key": toggle_key, "active": is_toggle_enabled(db, toggle_key, default=False), "activation_safe": False, "reason": exc.reason}
    return {"toggle_key": toggle_key, "active": is_toggle_enabled(db, toggle_key, default=False), "activation_safe": True, "reason": "projection_ready"}


@router.get("/jobs/{job_id}")
def read_job(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    row = db.query(ProjectionRebuildJob).filter(ProjectionRebuildJob.id == job_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Projection rebuild job not found")
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def _run(db: Session, kind: str, payload: ProjectionRebuildRequest, actor: str) -> dict[str, object]:
    kwargs = {"city_id": payload.city_id, "actor": actor, "source": payload.source, "audit_context": payload.audit_context}
    if kind == "published_place_snapshot":
        return rebuild_published_place_snapshots(db, **kwargs)
    if kind == "search_place_document":
        return rebuild_search_place_documents(db, **kwargs)
    if kind == "routing_place_node":
        return rebuild_routing_place_nodes(db, **kwargs)
    if kind == "route_candidate_set":
        return rebuild_route_candidate_sets(db, **kwargs)
    raise ValueError(f"Unsupported projection type: {kind}")


def _record_failure(db: Session, kind: str, payload: ProjectionRebuildRequest, actor: str, exc: Exception) -> None:
    row = ProjectionRebuildJob(projection_type=kind, city_id=payload.city_id, scope_key="global" if payload.city_id is None else f"city:{payload.city_id}", status="failed", actor=actor, source=payload.source, audit_context=payload.audit_context, failed_count=1, error_summary=type(exc).__name__)
    db.add(row); db.commit()
    log_rebuild_result(projection_type=kind, city_id=payload.city_id, status="failed", reason=type(exc).__name__)


def _job_payload(row: ProjectionRebuildJob | None) -> dict[str, object] | None:
    return None if row is None else {column.name: getattr(row, column.name) for column in row.__table__.columns}
