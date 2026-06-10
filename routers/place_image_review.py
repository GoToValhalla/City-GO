"""
Admin API очереди проверки фотографий мест.

Все endpoints защищены admin_required (Bearer-token).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.place_image import (
    PendingPlaceImageRead,
    PendingPlaceImagesResponse,
    PlaceImageActionResult,
    PlaceImageReviewAction,
)
from services.feature_toggle_guards import assert_photo_moderation
from services.place_image_review_service import (
    approve_place_image,
    get_pending_place_images,
    reject_place_image,
    set_primary_place_image,
)

router = APIRouter(prefix="/admin/place-images", tags=["admin-place-images"])


@router.get("/pending", response_model=PendingPlaceImagesResponse)
def read_pending_place_images(
    city_slug: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PendingPlaceImagesResponse:
    assert_photo_moderation(db)
    items, total = get_pending_place_images(
        db,
        city_slug=city_slug,
        limit=limit,
        offset=offset,
    )
    return PendingPlaceImagesResponse(
        items=[PendingPlaceImageRead.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{image_id}/approve", response_model=PlaceImageActionResult)
def post_approve_place_image(
    image_id: int,
    body: PlaceImageReviewAction | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceImageActionResult:
    # reviewer берётся из auth context; body.reviewer игнорируется (deprecated)
    try:
        image = approve_place_image(
            db,
            image_id,
            actor=auth.actor_id,
            comment=None if body is None else body.comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PlaceImageActionResult.model_validate(image)


@router.post("/{image_id}/reject", response_model=PlaceImageActionResult)
def post_reject_place_image(
    image_id: int,
    body: PlaceImageReviewAction | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceImageActionResult:
    # reviewer берётся из auth context; body.reviewer игнорируется (deprecated)
    try:
        image = reject_place_image(
            db,
            image_id,
            actor=auth.actor_id,
            comment=None if body is None else body.comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return PlaceImageActionResult.model_validate(image)


@router.post("/{image_id}/set-primary", response_model=PlaceImageActionResult)
def post_set_primary_place_image(
    image_id: int,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceImageActionResult:
    try:
        image = set_primary_place_image(db, image_id, actor=auth.actor_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PlaceImageActionResult.model_validate(image)
