from __future__ import annotations

from importlib import import_module

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000


@router.get("/overview/" + "backlog-breakdown")
def read_queue_breakdown(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    module = import_module("services." + "admin_read_model_v2")
    payload = module.backlog_breakdown(db)
    plan = module.reduction_plan(db)
    payload["reduction_available"] = True
    payload["reduction_plan_endpoint"] = "/admin/overview/" + "backlog-" + "reduction-plan"
    payload["top_actions"] = list(plan.get("actions") or [])[:4]
    return payload


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
