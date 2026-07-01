"""Admin ops: обзор, feature toggles, метрики."""

from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_coverage import AdminCoverageSummaryResponse, AdminCityCoverageRow
from schemas.admin_ops import (
    AdminActionCard,
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin-ops"])
ADMIN_READ_STATEMENT_TIMEOUT_MS = 3000


@router.get("/overview", response_model=AdminOverviewResponse)
def read_admin_overview(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminOverviewResponse:
    try:
        _apply_admin_read_timeout(db)
        return AdminOverviewResponse(**build_admin_overview(db))
    except (SQLAlchemyError, TimeoutError) as exc:
        db.rollback()
        logger.exception("Admin overview degraded", exc_info=exc)
        return _degraded_overview()


@router.get("/metrics/summary", response_model=AdminMetricsSummary)
def read_admin_metrics(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> AdminMetricsSummary:
    try:
        _apply_admin_read_timeout(db)
        return AdminMetricsSummary(**build_metrics_summary(db))
    except (SQLAlchemyError, TimeoutError) as exc:
        db.rollback()
        logger.exception("Admin metrics summary degraded", exc_info=exc)
        return _degraded_metrics()


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
    try:
        _apply_admin_read_timeout(db)
        return AdminVerificationSummary(**verification_queue_summary(db))
    except (SQLAlchemyError, TimeoutError) as exc:
        db.rollback()
        logger.exception("Admin verification summary degraded", exc_info=exc)
        return AdminVerificationSummary(queue_total=0, needs_recheck=0, unverified=0, low_confidence=0, verified_today=0)


@router.get("/coverage/summary", response_model=AdminCoverageSummaryResponse)
def read_coverage_summary(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminCoverageSummaryResponse:
    try:
        _apply_admin_read_timeout(db)
        items, total = build_coverage_summary(db, limit=limit, offset=offset)
        return AdminCoverageSummaryResponse(
            items=[AdminCityCoverageRow.model_validate(row) for row in items],
            total=total, limit=limit, offset=offset,
        )
    except (SQLAlchemyError, TimeoutError) as exc:
        db.rollback()
        logger.exception("Admin coverage summary degraded", exc_info=exc)
        return AdminCoverageSummaryResponse(items=[], total=0, limit=limit, offset=offset)


def _apply_admin_read_timeout(db: Session) -> None:
    bind = db.get_bind()
    if bind.dialect.name == "postgresql":
        db.execute(text(f"SET LOCAL statement_timeout = {ADMIN_READ_STATEMENT_TIMEOUT_MS}"))


def _degraded_overview() -> AdminOverviewResponse:
    return AdminOverviewResponse(
        critical=[
            AdminActionCard(
                code="admin_overview_degraded",
                title="Админка в деградированном режиме",
                count=1,
                severity="red",
                link_path="/admin/system-health",
                hint="Быстрый обзор не смог прочитать БД за лимит времени. Остальные разделы должны продолжить открываться.",
            )
        ],
        data_quality=[],
        operations=[],
        recent_audit_count=0,
        generated_at=datetime.utcnow(),
    )


def _degraded_metrics() -> AdminMetricsSummary:
    return AdminMetricsSummary(
        dau=0,
        mau=0,
        routes_built=0,
        routes_failed=0,
        avg_route_stops=0.0,
        routes_today=0,
        routes_week=0,
        routes_failed_week=0,
        route_success_rate=None,
        places_total=0,
        places_published=0,
        places_no_photo=0,
        places_no_address=0,
        places_no_description=0,
        imports_ok_week=0,
        imports_fail_week=0,
        enrichment_ok_week=0,
        ai_requests_week=0,
        data_collection_note="Admin metrics degraded: БД не ответила за быстрый лимит.",
    )
