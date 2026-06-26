"""Admin ops: обзор, feature toggles, метрики."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_coverage import AdminCoverageSummaryResponse, AdminCityCoverageRow
from schemas.admin_ops import (
    AdminMetricsSummary,
    AdminOverviewResponse,
    AdminVerificationSummary,
    FeatureToggleGroupRead,
    FeatureToggleListResponse,
    FeatureToggleRead,
    FeatureToggleUpdateRequest,
)
from services.admin_coverage_metrics import build_coverage_summary
from services.admin_metrics_service import build_metrics_summary
from services.admin_overview_service import build_admin_overview
from services.feature_toggle_service import list_city_toggles, list_global_toggles, list_groups, update_toggle
from services.local_persistent_cache import cache_stats
from services.verification_queue_summary import verification_queue_summary

router = APIRouter(prefix="/admin", tags=["admin-ops"])


@router.get("/overview", response_model=AdminOverviewResponse)
def read_admin_overview(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminOverviewResponse:
    return AdminOverviewResponse(**build_admin_overview(db))


@router.get("/metrics/summary", response_model=AdminMetricsSummary)
def read_admin_metrics(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminMetricsSummary:
    return AdminMetricsSummary(**build_metrics_summary(db))


@router.get("/cache/local")
def read_local_cache_stats(auth: AdminContext = Depends(admin_required)) -> dict[str, object]:
    return cache_stats()


@router.get("/feature-toggles/groups", response_model=list[FeatureToggleGroupRead])
def read_feature_toggle_groups(auth: AdminContext = Depends(admin_required)) -> list[FeatureToggleGroupRead]:
    return [FeatureToggleGroupRead.model_validate(row) for row in list_groups()]


@router.get("/feature-toggles", response_model=FeatureToggleListResponse)
def read_feature_toggles(
    scope: str = Query(default="global"),
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> FeatureToggleListResponse:
    if scope == "city":
        if not city_slug:
            raise HTTPException(status_code=422, detail="Для scope=city укажите city_slug")
        items = [FeatureToggleRead(**row) for row in list_city_toggles(db, city_slug)]
    else:
        items = [FeatureToggleRead(**row) for row in list_global_toggles(db)]
    return FeatureToggleListResponse(items=items, total=len(items))


@router.put("/feature-toggles/{key}", response_model=FeatureToggleRead)
def put_feature_toggle(
    key: str,
    payload: FeatureToggleUpdateRequest,
    scope: str = Query(default="global"),
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> FeatureToggleRead:
    scope_id = city_slug if scope == "city" else None
    try:
        row = update_toggle(db, key=key, scope=scope, scope_id=scope_id, value_bool=payload.value_bool, actor=auth.actor_id, reason=payload.reason)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FeatureToggleRead(key=row.key, scope=row.scope, scope_id=row.scope_id, value_bool=row.value_bool, description=row.description, updated_by=row.updated_by, updated_at=row.updated_at)


@router.get("/place-verifications/summary", response_model=AdminVerificationSummary)
def read_verification_summary(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminVerificationSummary:
    return AdminVerificationSummary(**verification_queue_summary(db))


@router.get("/coverage/summary", response_model=AdminCoverageSummaryResponse)
def read_coverage_summary(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCoverageSummaryResponse:
    items, total = build_coverage_summary(db, limit=limit, offset=offset)
    return AdminCoverageSummaryResponse(
        items=[AdminCityCoverageRow.model_validate(row) for row in items],
        total=total, limit=limit, offset=offset,
    )