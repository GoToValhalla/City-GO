from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_route_health import RouteHealthRerunResponse, RouteHealthSummary
from services.admin_route_health_service import build_route_health_summary

router = APIRouter(prefix="/admin/route-health", tags=["admin-route-health"])


@router.get("", response_model=RouteHealthSummary)
def read_route_health(
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteHealthSummary:
    try:
        return build_route_health_summary(db, city_slug=city_slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/re-run", response_model=RouteHealthRerunResponse)
def rerun_route_health(
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> RouteHealthRerunResponse:
    try:
        result = build_route_health_summary(db, city_slug=city_slug)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RouteHealthRerunResponse(status="completed", result=result)
