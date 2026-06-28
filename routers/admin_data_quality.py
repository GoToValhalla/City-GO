"""Admin data quality foundation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from schemas.data_quality import (
    DataQualityBulkRequest,
    DataQualityBulkResponse,
    DataQualityIssueListResponse,
    DataQualityRefreshRequest,
)
from services.data_quality import (
    apply_bulk_action,
    build_data_quality_summary,
    list_data_quality_issues,
    list_possible_duplicate_groups,
    preview_bulk_action,
    refresh_data_quality_issues,
)

router = APIRouter(prefix="/admin/data-quality", tags=["admin-data-quality"])


@router.get("/summary")
def get_data_quality_summary(
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return build_data_quality_summary(db)


@router.get("/duplicates")
def get_possible_duplicate_groups(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    filters = {"city_id": city_id, "city_slug": city_slug, "status": status, "severity": severity}
    items, total = list_possible_duplicate_groups(db, filters=filters, limit=limit, offset=offset)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/issues", response_model=DataQualityIssueListResponse)
def get_data_quality_issues(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    issue_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    published: bool | None = Query(default=None),
    route_eligible: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DataQualityIssueListResponse:
    filters = {
        "city_id": city_id, "city_slug": city_slug, "issue_type": issue_type,
        "status": status, "severity": severity, "published": published, "route_eligible": route_eligible,
    }
    items, total = list_data_quality_issues(db, filters=filters, limit=limit, offset=offset)
    return DataQualityIssueListResponse(items=items, total=total, limit=limit, offset=offset)


@router.post("/issues/refresh")
def refresh_data_quality(
    payload: DataQualityRefreshRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    body = payload or DataQualityRefreshRequest()
    _ensure_city_exists(db, body.city_id)
    return refresh_data_quality_issues(
        db, city_id=body.city_id, limit=body.limit, dry_run=body.dry_run,
    ).as_dict()


@router.post("/bulk-actions/preview", response_model=DataQualityBulkResponse)
def preview_data_quality_bulk_action(
    payload: DataQualityBulkRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DataQualityBulkResponse:
    try:
        return DataQualityBulkResponse.model_validate(preview_bulk_action(db, payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/bulk-actions/apply", response_model=DataQualityBulkResponse)
def apply_data_quality_bulk_action(
    payload: DataQualityBulkRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> DataQualityBulkResponse:
    try:
        result = apply_bulk_action(db, payload.model_dump(), actor=auth.actor_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return DataQualityBulkResponse.model_validate(result)


def _ensure_city_exists(db: Session, city_id: int | None) -> None:
    if city_id is None:
        return
    if db.query(City).filter(City.id == city_id).first() is None:
        raise HTTPException(status_code=404, detail="Город не найден")