from __future__ import annotations

from importlib import import_module

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.admin_operation import AdminOperation

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000


@router.get("/overview/" + "backlog-breakdown")
def read_queue_breakdown(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    try:
        module = import_module("services." + "admin_read_model_v2")
        payload = module.backlog_breakdown(db)
        plan = module.reduction_plan(db)
    except Exception:
        db.rollback()
        from services.admin_backlog_breakdown_service import build_admin_backlog_breakdown
        from services.admin_backlog_reduction_service import build_reduction_plan

        payload = build_admin_backlog_breakdown(db)
        plan = build_reduction_plan(db)
    payload["reduction_available"] = True
    payload["reduction_plan_endpoint"] = "/admin/overview/" + "backlog-" + "reduction-plan"
    payload["top_actions"] = list(plan.get("actions") or [])[:4]
    payload["last_reduction_result"] = _latest_reduction_result(db)
    return payload


def _latest_reduction_result(db: Session) -> dict[str, object] | None:
    operation = (
        db.query(AdminOperation)
        .filter(AdminOperation.operation_type == "backlog_reduction")
        .order_by(AdminOperation.id.desc())
        .first()
    )
    if operation is None:
        return None
    result = operation.result or {}
    return {
        "job_id": operation.id,
        "status": operation.status,
        "action_code": result.get("action_code"),
        "changed_count": result.get("changed_count", 0),
        "queued_count": result.get("queued_count", 0),
        "failed_count": result.get("failed_count", 0),
    }


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
