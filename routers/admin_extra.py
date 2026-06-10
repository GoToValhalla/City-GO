from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.admin_extra import (
    AdminCoverageResponse,
    AdminRoleListResponse,
    AdminRoleRead,
    AdminRouteFeedbackListResponse,
    AdminRouteFeedbackRead,
)
from services.admin_extra_service import ADMIN_ROLES, admin_coverage, admin_route_feedback

router = APIRouter(prefix="/admin", tags=["admin-extra"])


@router.get("/roles", response_model=AdminRoleListResponse)
def read_admin_roles() -> AdminRoleListResponse:
    return AdminRoleListResponse(items=[AdminRoleRead.model_validate(role) for role in ADMIN_ROLES])


@router.get("/cities/{city_id}/coverage", response_model=AdminCoverageResponse)
def read_admin_city_coverage(city_id: int, db: Session = Depends(get_db)) -> AdminCoverageResponse:
    payload = admin_coverage(db, city_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Город не найден")
    return AdminCoverageResponse.model_validate(payload)


@router.get("/route-feedback", response_model=AdminRouteFeedbackListResponse)
def read_admin_route_feedback(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AdminRouteFeedbackListResponse:
    items, total = admin_route_feedback(db, limit=limit, offset=offset)
    return AdminRouteFeedbackListResponse(
        items=[AdminRouteFeedbackRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
