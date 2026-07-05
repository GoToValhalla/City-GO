from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from schemas.admin_emergency_hide import EmergencyHideRequest, EmergencyHideResponse
from services.admin_emergency_hide_service import emergency_hide_place

router = APIRouter(prefix="/admin", tags=["admin-emergency-hide"])


@router.post("/places/{place_id}/emergency-hide", response_model=EmergencyHideResponse)
def hide_place_emergency(
    place_id: int,
    body: EmergencyHideRequest,
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> EmergencyHideResponse:
    try:
        place, audit, replay = emergency_hide_place(
            db,
            place_id=place_id,
            actor=auth.actor_id,
            reason=body.reason,
            idempotency_key=body.idempotency_key,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return EmergencyHideResponse(
        place_id=place.id,
        status=place.status,
        publication_status=place.publication_status,
        is_published=place.is_published,
        is_visible_in_catalog=place.is_visible_in_catalog,
        is_route_eligible=place.is_route_eligible,
        audit_log_id=audit.id,
        idempotent_replay=replay,
        reason=body.reason,
        hidden_at=place.unpublished_at or place.updated_at,
    )
