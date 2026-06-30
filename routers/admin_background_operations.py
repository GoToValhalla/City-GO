"""Admin background operation endpoints for heavy refresh/recalculate jobs."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.admin_background_operation_service import (
    OP_CITY_READINESS_RECALCULATE,
    OP_COVERAGE_GAPS_REFRESH,
    create_background_operation,
    get_operation,
    latest_operation,
    operation_payload,
    run_background_operation,
)

router = APIRouter(prefix="/admin/background-operations", tags=["admin-background-operations"])


class CoverageGapsRefreshRequest(BaseModel):
    city_slug: str | None = None


class CityReadinessRecalculateRequest(BaseModel):
    city_slug: str
    recalculate_place_scores: bool = True
    reason: str | None = None


@router.post("/coverage-gaps/refresh")
def queue_coverage_gaps_refresh(
    background_tasks: BackgroundTasks,
    payload: CoverageGapsRefreshRequest | None = None,
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    body = payload or CoverageGapsRefreshRequest(city_slug=city_slug)
    target_city = body.city_slug or city_slug
    op = create_background_operation(
        db,
        operation_type=OP_COVERAGE_GAPS_REFRESH,
        actor=auth.actor_id,
        city_slug=target_city,
        params={"city_slug": target_city} if target_city else {},
    )
    if op.status == "queued":
        background_tasks.add_task(run_background_operation, op.id)
    return operation_payload(op) or {}


@router.post("/city-readiness/recalculate")
def queue_city_readiness_recalculate(
    background_tasks: BackgroundTasks,
    payload: CityReadinessRecalculateRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    op = create_background_operation(
        db,
        operation_type=OP_CITY_READINESS_RECALCULATE,
        actor=auth.actor_id,
        city_slug=payload.city_slug,
        params=payload.model_dump(),
    )
    if op.status == "queued":
        background_tasks.add_task(run_background_operation, op.id)
    return operation_payload(op) or {}


@router.get("/{operation_id}")
def read_background_operation(
    operation_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    op = get_operation(db, operation_id)
    if op is None:
        raise HTTPException(status_code=404, detail="Операция не найдена")
    return operation_payload(op) or {}


@router.get("/latest/status")
def read_latest_background_operation(
    operation_type: str = Query(...),
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    op = latest_operation(db, operation_type=operation_type, city_slug=city_slug)
    if op is None:
        return {"operation_type": operation_type, "city_slug": city_slug, "status": "missing", "operation": None}
    return {"operation_type": operation_type, "city_slug": city_slug, "status": op.status, "operation": operation_payload(op)}
