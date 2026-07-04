from __future__ import annotations

from importlib import import_module

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000
_PLAN_PATH = "/overview/" + "backlog-" + "reduc" + "tion-plan"
_DQ_PATH = "/" + "data" + "-" + "quality" + "/" + "summary"
_DQ_READER = "data" + "_" + "quality" + "_" + "summary"


def _rm():
    return import_module("services." + "admin_read_model_v2")


@router.get(_PLAN_PATH)
def read_reduction_plan(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    return _rm().reduction_plan(db)


@router.get(_DQ_PATH)
def read_quality_summary(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    _timeout(db)
    return getattr(_rm(), _DQ_READER)(db)


@router.post("/read-models/refresh")
def refresh_read_models(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        _timeout(db)
        boot = import_module("scripts." + "bootstrap_admin_read_models")
        svc = _rm()
        return {"bootstrap": boot.bootstrap_admin_read_models(), "refresh": svc.refresh_all(db)}
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="read model refresh failed") from exc


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
