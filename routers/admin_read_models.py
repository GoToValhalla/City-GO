from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db

router = APIRouter(prefix="/admin", tags=["admin-read-models"])
ADMIN_READ_MODEL_TIMEOUT_MS = 3000


@router.post("/read-models/refresh")
def refresh_read_models(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    try:
        _timeout(db)
        from services.admin_read_model_v2 import refresh_all

        return refresh_all(db)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Не удалось обновить read models админки") from exc


def _timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_MODEL_TIMEOUT_MS}"))
