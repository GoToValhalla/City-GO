from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.debug_report import (
    DebugReportCreate,
    DebugReportCreateResponse,
    DebugReportListResponse,
    DebugReportRead,
)
from services.debug_report_service import create_debug_report, get_debug_report, list_debug_reports

router = APIRouter(tags=["debug-reports"])


@router.post("/debug-reports", response_model=DebugReportCreateResponse)
def create_public_debug_report(payload: DebugReportCreate, db: Session = Depends(get_db)) -> DebugReportCreateResponse:
    row = create_debug_report(db, payload)
    db.commit()
    db.refresh(row)
    # Public response: no admin URL, no provider transport errors.
    return DebugReportCreateResponse(
        report_id=row.id,
        public_id=row.public_id,
        status="accepted",
        telegram_status="queued" if not row.telegram_sent else "sent",
    )


@router.get("/admin/debug-reports", response_model=DebugReportListResponse)
def list_admin_debug_reports(
    city_slug: str | None = None,
    screen: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    request_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DebugReportListResponse:
    del auth
    items, total = list_debug_reports(
        db,
        city_slug=city_slug,
        screen=screen,
        category=category,
        severity=severity,
        request_id=request_id,
        limit=limit,
        offset=offset,
    )
    return DebugReportListResponse(
        items=[DebugReportRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/admin/debug-reports/{id_or_public_id}", response_model=DebugReportRead)
def read_admin_debug_report(
    id_or_public_id: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DebugReportRead:
    del auth
    row = get_debug_report(db, id_or_public_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Debug report not found")
    return DebugReportRead.model_validate(row)
