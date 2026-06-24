"""Admin operational center endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_platform import AlertListResponse, AlertRead, AlertTransitionRequest
from services.admin_platform_alerts import list_alerts, transition_alert
from services.admin_platform_analytics import analytics_summary
from services.admin_platform_health import health_summary
from services.admin_platform_quality import quality_summary

router = APIRouter(prefix="/admin", tags=["admin-platform"])


@router.get("/quality")
def read_quality(
    city_slug: str | None = None, region: str | None = None,
    category: str | None = None, severity: str | None = None,
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> dict[str, object]:
    return quality_summary(db, city_slug=city_slug, region=region, category=category, severity=severity)


@router.get("/system-health")
def read_health(
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> dict[str, object]:
    return health_summary(db)


@router.get("/system-health/alerts", response_model=AlertListResponse)
def read_alerts(
    status: str | None = None, limit: int = Query(50, ge=1, le=200),
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> AlertListResponse:
    items = list_alerts(db, status=status, limit=limit)
    return AlertListResponse(items=[AlertRead.model_validate(row) for row in items], total=len(items))


@router.post("/system-health/alerts/{log_id}", response_model=AlertRead)
def update_alert(
    log_id: int, body: AlertTransitionRequest,
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> AlertRead:
    row = transition_alert(db, log_id, status=body.status, actor=auth.actor_id)
    if row is None:
        raise HTTPException(404, "Системный лог не найден")
    return AlertRead.model_validate(row)


@router.get("/analytics")
def read_analytics(
    days: int = Query(30, ge=1, le=365), city_slug: str | None = None,
    channel: str | None = Query(None, pattern="^(web|telegram)$"),
    region: str | None = None, category: str | None = None, environment: str | None = None,
    auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db),
) -> dict[str, object]:
    return analytics_summary(
        db, days=days, city_slug=city_slug, channel=channel,
        region=region, category=category, environment=environment,
    )
