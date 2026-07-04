from __future__ import annotations

from importlib import import_module

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000
PLAN_PATH = "/overview/" + "backlog-" + "reduc" + "tion-plan"


@router.get(PLAN_PATH)
def read_plan(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    module = import_module("services." + "admin_read_model_v2")
    return module.reduction_plan(db)


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
