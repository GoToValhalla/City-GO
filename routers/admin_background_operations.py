"""Admin background operation endpoints for heavy refresh/recalculate jobs."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from models.known_missing_poi import KnownMissingPoi
from services.admin_background_operation_service import (
    OP_CITY_READINESS_RECALCULATE,
    OP_COVERAGE_GAPS_REFRESH,
    create_background_operation,
    get_operation,
    latest_operation,
    operation_payload,
    run_background_operation,
    snapshot_status_payload,
)
from services.city_readiness import latest_city_readiness_snapshot

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


@router.get("/coverage-gaps/status")
def read_coverage_gaps_operation_status(
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    latest = latest_operation(db, operation_type=OP_COVERAGE_GAPS_REFRESH, city_slug=city_slug)
    snapshot = snapshot_status_payload(last_snapshot_at=_coverage_last_snapshot_at(db, city_slug=city_slug), latest=latest)
    return {"operation_type": OP_COVERAGE_GAPS_REFRESH, "city_slug": city_slug, **snapshot}


@router.get("/city-readiness/status")
def read_city_readiness_operation_status(
    city_slug: str = Query(...),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    latest = latest_operation(db, operation_type=OP_CITY_READINESS_RECALCULATE, city_slug=city_slug)
    snapshot = latest_city_readiness_snapshot(db, city_slug=city_slug)
    return {
        "operation_type": OP_CITY_READINESS_RECALCULATE,
        "city_slug": city_slug,
        **snapshot_status_payload(last_snapshot_at=snapshot.created_at if snapshot else None, latest=latest),
    }


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


def _coverage_last_snapshot_at(db: Session, *, city_slug: str | None) -> datetime | None:
    query = db.query(func.max(KnownMissingPoi.last_checked_at)).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    return query.scalar()
