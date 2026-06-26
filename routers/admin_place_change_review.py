from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.place_change_review import (
    AdminPlaceChangeReviewActionRequest,
    AdminPlaceChangeReviewActionResponse,
    AdminPlaceChangeReviewListResponse,
    AdminPlaceChangeReviewRead,
)
from services.place_change_review_service import (
    approve_place_change_review,
    list_place_change_reviews,
    reject_place_change_review,
)

router = APIRouter(prefix="/admin/place-change-reviews", tags=["admin-place-change-reviews"])


@router.get("", response_model=AdminPlaceChangeReviewListResponse)
def read_place_change_reviews(
    city_slug: str | None = Query(default=None),
    status: str = Query(default="open"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceChangeReviewListResponse:
    items, total = list_place_change_reviews(
        db,
        city_slug=city_slug,
        status=status,
        limit=limit,
        offset=offset,
    )
    return AdminPlaceChangeReviewListResponse(
        items=[AdminPlaceChangeReviewRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{review_id}/approve", response_model=AdminPlaceChangeReviewActionResponse)
def approve_review(
    review_id: int,
    payload: AdminPlaceChangeReviewActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceChangeReviewActionResponse:
    item = approve_place_change_review(
        db,
        review_id,
        actor=auth.actor_id,
        reason=payload.reason if payload else None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Открытая проверка изменения не найдена")
    return AdminPlaceChangeReviewActionResponse(
        item=AdminPlaceChangeReviewRead.model_validate(item),
        message="Изменение принято.",
    )


@router.post("/{review_id}/reject", response_model=AdminPlaceChangeReviewActionResponse)
def reject_review(
    review_id: int,
    payload: AdminPlaceChangeReviewActionRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> AdminPlaceChangeReviewActionResponse:
    item = reject_place_change_review(
        db,
        review_id,
        actor=auth.actor_id,
        reason=payload.reason if payload else None,
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Открытая проверка изменения не найдена")
    return AdminPlaceChangeReviewActionResponse(
        item=AdminPlaceChangeReviewRead.model_validate(item),
        message="Изменение отклонено, прежние данные места восстановлены.",
    )
