from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_review import ReviewItemRead
from schemas.destination_data_pipeline import DestinationPipelineRunList, DestinationPipelineRunRequest, DestinationPipelineRunResponse, DestinationReadinessRead
from services.admin_destination_pipeline_application import latest, list_runs, read_run, readiness, recalculate, review_items, start, stop
from services.destination_data_pipeline_service import DestinationPipelinePreconditionError

router = APIRouter(prefix="/admin/destinations", tags=["admin-destination-pipeline"])


@router.post("/{slug}/data-pipeline/run", response_model=DestinationPipelineRunResponse)
def run_destination_pipeline(slug: str, body: DestinationPipelineRunRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    try:
        return start(db, slug, body, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DestinationPipelinePreconditionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/{slug}/data-pipeline/latest", response_model=DestinationPipelineRunResponse | None)
def read_latest_destination_pipeline(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    try:
        return latest(db, slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{slug}/data-pipeline/runs", response_model=DestinationPipelineRunList)
def list_destination_pipeline_runs(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db), limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> DestinationPipelineRunList:
    try:
        return list_runs(db, slug, limit=limit, offset=offset)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{slug}/data-pipeline/runs/{run_id}", response_model=DestinationPipelineRunResponse)
def read_destination_pipeline_run(slug: str, run_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    try:
        return read_run(db, slug, run_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{slug}/data-pipeline/runs/{run_id}/stop", response_model=DestinationPipelineRunResponse)
def stop_destination_pipeline_run(slug: str, run_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    try:
        return stop(db, slug, run_id, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{slug}/memberships/recalculate")
def recalculate_destination_memberships_endpoint(slug: str, scope_id: int | None = None, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    try:
        return recalculate(db, slug, scope_id, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{slug}/readiness", response_model=DestinationReadinessRead)
def read_destination_readiness(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationReadinessRead:
    try:
        return readiness(db, slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{slug}/review-items", response_model=list[ReviewItemRead])
def read_destination_review_items(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[ReviewItemRead]:
    try:
        return review_items(db, slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
