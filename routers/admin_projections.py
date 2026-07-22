"""Authenticated Stage 5 rebuild, readiness, and rollout controls."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.projection_operations import ProjectionReadinessResponse, ProjectionRebuildRequest
from services.public_read_projection_service import PublicReadProjectionError
from services.projection_activation_service import TOGGLE_PROJECTIONS
from services.admin_projection_application import (
    ProjectionRebuildFailed,
    activation_safety,
    job_payload,
    readiness,
    rebuild,
)

router = APIRouter(prefix="/admin/projections", tags=["admin-projections"])
KINDS = {"snapshot": "published_place_snapshot", "search": "search_place_document", "catalog": "search_place_document", "routing": "routing_place_node", "route_candidate_set": "route_candidate_set"}


@router.post("/rebuild")
def start_rebuild(payload: ProjectionRebuildRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    kind = KINDS.get(payload.projection_type, payload.projection_type)
    try:
        return rebuild(db, payload, actor=auth.actor_id, kind=kind)
    except (ValueError, PublicReadProjectionError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ProjectionRebuildFailed as exc:
        raise HTTPException(status_code=500, detail="Projection rebuild failed") from exc


@router.get("/readiness", response_model=ProjectionReadinessResponse)
def read_readiness(projection_type: str = Query(...), city_id: int | None = Query(default=None), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> ProjectionReadinessResponse:
    kind = KINDS.get(projection_type, projection_type)
    return ProjectionReadinessResponse(**readiness(db, kind=kind, city_id=city_id))


@router.get("/activation-safety")
def read_activation_safety(toggle_key: str = Query(...), auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    if toggle_key not in TOGGLE_PROJECTIONS:
        raise HTTPException(status_code=422, detail="Unsupported projection toggle")
    return activation_safety(db, toggle_key)


@router.get("/jobs/{job_id}")
def read_job(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    payload = job_payload(db, job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Projection rebuild job not found")
    return payload
