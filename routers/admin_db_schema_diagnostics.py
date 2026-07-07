"""Admin read-only DB schema diagnostics."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_db_schema_diagnostics import AdminDbSchemaDiagnosticsResponse
from services.admin_schema_diagnostics import build_db_schema_diagnostics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/diagnostics", tags=["admin-diagnostics"])


@router.get("/db-schema", response_model=AdminDbSchemaDiagnosticsResponse)
def read_db_schema_diagnostics(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminDbSchemaDiagnosticsResponse:
    del auth
    try:
        payload = build_db_schema_diagnostics(db.get_bind().engine)
        return AdminDbSchemaDiagnosticsResponse.model_validate(payload)
    except SQLAlchemyError as exc:
        logger.exception("Admin DB schema diagnostics failed", exc_info=exc)
        db.rollback()
        raise
