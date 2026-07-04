from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_backlog_breakdown import AdminBacklogBreakdownResponse
from schemas.admin_backlog_reduction import BacklogReductionPlan
from schemas.admin_ops import AdminOverviewResponse
from services.admin_read_model_v2 import admin_overview, backlog_breakdown, data_quality_summary, reduction_plan, refresh_all

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000


@router.get("/overview", response_model=AdminOverviewResponse)
def read_overview_from_model(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminOverviewResponse:
    _timeout(db)
    return AdminOverviewResponse(**admin_overview(db))


@router.get("/overview/backlog-breakdown", response_model=AdminBacklogBreakdownResponse)
def read_backlog_from_model(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminBacklogBreakdownResponse:
    _timeout(db)
    payload = backlog_breakdown(db)
    plan = reduction_plan(db)
    payload["reduction_available"] = True
    payload["reduction_plan_endpoint"] = "/admin/overview/backlog-reduction-plan"
    payload["top_actions"] = list(plan.get("actions") or [])[:4]
    return AdminBacklogBreakdownResponse(**payload)


@router.get("/overview/backlog-reduction-plan", response_model=BacklogReductionPlan)
def read_reduction_plan_from_model(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> BacklogReductionPlan:
    _timeout(db)
    return BacklogReductionPlan(**reduction_plan(db))


@router.get("/data-quality/summary")
def read_data_quality_from_model(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    return data_quality_summary(db)


@router.post("/read-models/refresh")
def refresh_read_models(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        _timeout(db)
        return refresh_all(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Не удалось обновить read models админки") from exc


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
