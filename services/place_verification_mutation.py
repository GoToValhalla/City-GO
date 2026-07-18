"""Canonical non-committing mutation for administrator place verification."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.place import Place
from services.admin_audit_service import write_admin_audit_log


def verify_locked_place(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str | None = None,
    action: str = "verify_place",
) -> None:
    """Verify an attached/pre-locked Place without owning the transaction."""

    if not str(actor or "").strip():
        raise ValueError("verification actor is required")
    if place.verification_status == "verified" and place.existence_confidence_level == "high":
        raise ValueError("Место уже подтверждено")

    old_value = {
        "verification_status": place.verification_status,
        "existence_confidence_level": place.existence_confidence_level,
        "existence_confidence_score": place.existence_confidence_score,
        "verified_by": place.verified_by,
        "verified_at": place.verified_at.isoformat() if place.verified_at else None,
    }
    place.verification_status = "verified"
    place.existence_confidence_level = "high"
    place.existence_confidence_score = max(place.existence_confidence_score or 0, 90)
    place.verified_by = actor
    place.verified_at = datetime.now(timezone.utc)
    place.verification_comment = reason

    write_admin_audit_log(
        db,
        actor=actor,
        action=action,
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value={
            "verification_status": place.verification_status,
            "existence_confidence_level": place.existence_confidence_level,
            "existence_confidence_score": place.existence_confidence_score,
            "verified_by": place.verified_by,
            "verified_at": place.verified_at.isoformat(),
        },
        reason=reason,
    )
    db.flush()
