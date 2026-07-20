from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.place_verification import (
    PlaceVerificationQueueResponse,
    PlaceVerificationRequest,
    PlaceVerificationResult,
    PlaceVerificationStats,
)
from services.place_verification_service import (
    apply_place_verification,
    get_place_verification_queue,
    place_verification_stats,
)

router = APIRouter(prefix="/verification", tags=["verification"])


@router.get("/queue/{city_slug}", response_model=PlaceVerificationQueueResponse)
def read_verification_queue(
    city_slug: str,
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceVerificationQueueResponse:
    del auth
    items, total = get_place_verification_queue(
        db,
        city_slug=city_slug,
        status=status,
        limit=limit,
        offset=offset,
    )
    return PlaceVerificationQueueResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/stats/{city_slug}", response_model=PlaceVerificationStats)
def read_verification_stats(
    city_slug: str,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceVerificationStats:
    del auth
    return PlaceVerificationStats(**place_verification_stats(db, city_slug))


@router.post("/place/{place_id}/confirm", response_model=PlaceVerificationResult)
def confirm_place(
    place_id: int,
    body: PlaceVerificationRequest | None = None,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceVerificationResult:
    del auth
    payload = body or PlaceVerificationRequest(action="exists")
    return _apply(place_id, payload.model_copy(update={"action": "exists"}), db)


@router.post("/place/{place_id}/reject", response_model=PlaceVerificationResult)
def reject_place(
    place_id: int,
    body: PlaceVerificationRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> PlaceVerificationResult:
    del auth
    action = body.action if body.action != "exists" else "needs_recheck"
    return _apply(place_id, body.model_copy(update={"action": action}), db)


def _apply(place_id: int, body: PlaceVerificationRequest, db: Session) -> PlaceVerificationResult:
    try:
        place = apply_place_verification(
            db,
            place_id,
            action=body.action,
            verifier=body.verifier,
            verifier_lat=body.verifier_lat,
            verifier_lng=body.verifier_lng,
            photo_url=body.photo_url,
            comment=body.comment,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Place not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_REQUEST", "message": "Invalid verification request"}) from exc

    return PlaceVerificationResult(
        place_id=place.id,
        title=place.title,
        status=place.status,
        is_active=place.is_active,
        existence_confidence_score=place.existence_confidence_score,
        existence_confidence_level=place.existence_confidence_level,
        verification_status=place.verification_status,
        verification_source=place.verification_source,
        verification_method=place.verification_method,
        verified_at=place.verified_at,
        verified_by=place.verified_by,
        verification_comment=place.verification_comment,
    )
