from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.destination_data_pipeline import DestinationDataPipelineRun
from models.place import Place
from models.place_merge_review import ReviewItem
from schemas.admin_review import ReviewItemRead
from schemas.destination_data_pipeline import DestinationPipelineRunList, DestinationPipelineRunRequest, DestinationPipelineRunResponse, DestinationReadinessRead
from services.admin_audit_service import write_admin_audit_log
from services.city_destination_compatibility import get_destination_by_slug
from services.destination_data_pipeline_service import DestinationPipelinePreconditionError, start_destination_pipeline, stop_destination_pipeline
from services.destination_pipeline_recalc import recalculate_destination_memberships
from services.destination_pipeline_runs import latest_run, serialize_run
from services.destination_readiness_service import build_destination_readiness

router = APIRouter(prefix="/admin/destinations", tags=["admin-destination-pipeline"])


@router.post("/{slug}/data-pipeline/run", response_model=DestinationPipelineRunResponse)
def run_destination_pipeline(slug: str, body: DestinationPipelineRunRequest, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    dest = _destination(db, slug)
    try:
        run = start_destination_pipeline(db, dest, body, actor=auth.actor_id)
    except DestinationPipelinePreconditionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return DestinationPipelineRunResponse(run=serialize_run(run, dest), message=run.message or "Прогон обработан")


@router.get("/{slug}/data-pipeline/latest", response_model=DestinationPipelineRunResponse | None)
def read_latest_destination_pipeline(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    dest = _destination(db, slug)
    run = latest_run(db, dest.id)
    return None if run is None else DestinationPipelineRunResponse(run=serialize_run(run, dest), message=run.message or "Последний прогон")


@router.get("/{slug}/data-pipeline/runs", response_model=DestinationPipelineRunList)
def list_destination_pipeline_runs(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db), limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)) -> DestinationPipelineRunList:
    dest = _destination(db, slug)
    query = db.query(DestinationDataPipelineRun).filter_by(destination_id=dest.id)
    rows = query.order_by(DestinationDataPipelineRun.created_at.desc()).offset(offset).limit(limit).all()
    return DestinationPipelineRunList(items=[serialize_run(row, dest) for row in rows], total=query.count(), limit=limit, offset=offset)


@router.get("/{slug}/data-pipeline/runs/{run_id}", response_model=DestinationPipelineRunResponse)
def read_destination_pipeline_run(slug: str, run_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    dest = _destination(db, slug)
    run = _run(db, dest.id, run_id)
    return DestinationPipelineRunResponse(run=serialize_run(run, dest), message=run.message or "Детали прогона")


@router.post("/{slug}/data-pipeline/runs/{run_id}/stop", response_model=DestinationPipelineRunResponse)
def stop_destination_pipeline_run(slug: str, run_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationPipelineRunResponse:
    dest = _destination(db, slug)
    try:
        run = stop_destination_pipeline(db, _run(db, dest.id, run_id), actor=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return DestinationPipelineRunResponse(run=serialize_run(run, dest), message=run.message or "Прогон остановлен")


@router.post("/{slug}/memberships/recalculate")
def recalculate_destination_memberships_endpoint(slug: str, scope_id: int | None = None, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)):
    dest = _destination(db, slug)
    counters = {"memberships_created": 0, "memberships_updated": 0, "errors_count": 0}
    result = recalculate_destination_memberships(db, dest, counters, [scope_id] if scope_id else None)
    write_admin_audit_log(db, actor=auth.actor_id, action="destination_memberships_recalculated", entity_type="destination", entity_id=dest.id, new_value=result | counters)
    db.commit()
    return {"status": "ok", "message": "Принадлежность мест пересчитана", "result": result | counters}


@router.get("/{slug}/readiness", response_model=DestinationReadinessRead)
def read_destination_readiness(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> DestinationReadinessRead:
    dest = _destination(db, slug)
    result = build_destination_readiness(db, dest)
    db.commit()
    return result


@router.get("/{slug}/review-items", response_model=list[ReviewItemRead])
def read_destination_review_items(slug: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> list[ReviewItemRead]:
    dest = _destination(db, slug)
    rows = db.query(ReviewItem, Place.title).join(Place, Place.id == ReviewItem.place_id).filter(ReviewItem.status == "pending", Place.destination_memberships.any(destination_id=dest.id)).order_by(ReviewItem.created_at.desc()).limit(100).all()
    return [ReviewItemRead(id=item.id, place_id=item.place_id, place_name=title, source=item.source, confidence=item.confidence, status=item.status, reason=item.reason, created_at=item.created_at, place_version_at_creation=item.place_version_at_creation) for item, title in rows]


def _destination(db: Session, slug: str):
    dest = get_destination_by_slug(db, slug)
    if dest is None:
        raise HTTPException(status_code=404, detail="Направление не найдено")
    return dest


def _run(db: Session, destination_id: int, run_id: int) -> DestinationDataPipelineRun:
    run = db.query(DestinationDataPipelineRun).filter_by(destination_id=destination_id, id=run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Прогон не найден")
    return run
