"""Canonical non-committing mutation for Place verification state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from services.admin_audit_service import write_admin_audit_log

_ALLOWED_VERIFICATION_STATUSES = frozenset({"verified", "trusted", "rejected"})


def transition_place_verification(
    db: Session,
    place: Place,
    *,
    to_status: str,
    actor: str,
    reason: str | None = None,
    action: str = "transition_place_verification",
    verification_source: str | None = None,
    verification_method: str | None = None,
    reject_noop: bool = False,
) -> bool:
    """Apply the complete verification state without committing."""
    if not str(actor or "").strip():
        raise ValueError("verification actor is required")
    if to_status not in _ALLOWED_VERIFICATION_STATUSES:
        raise ValueError(f"unsupported verification status: {to_status}")

    target_level = "high" if to_status in {"verified", "trusted"} else "low"
    target_score = max(place.existence_confidence_score or 0, 90) if target_level == "high" else 0
    is_noop = (
        place.verification_status == to_status
        and place.existence_confidence_level == target_level
        and int(place.existence_confidence_score or 0) == int(target_score)
        and place.verified_by == actor
    )
    if is_noop:
        if reject_noop:
            raise ValueError("Состояние проверки уже установлено")
        return False

    old_value = {
        "verification_status": place.verification_status,
        "verification_source": place.verification_source,
        "verification_method": place.verification_method,
        "existence_confidence_level": place.existence_confidence_level,
        "existence_confidence_score": place.existence_confidence_score,
        "verified_by": place.verified_by,
        "verified_at": place.verified_at.isoformat() if place.verified_at else None,
    }
    place.verification_status = to_status
    place.verification_source = verification_source
    place.verification_method = verification_method
    place.existence_confidence_level = target_level
    place.existence_confidence_score = target_score
    place.verified_by = actor
    place.verified_at = datetime.utcnow()
    place.needs_recheck_at = None
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
            "verification_source": place.verification_source,
            "verification_method": place.verification_method,
            "existence_confidence_level": place.existence_confidence_level,
            "existence_confidence_score": place.existence_confidence_score,
            "verified_by": place.verified_by,
            "verified_at": place.verified_at.isoformat(),
        },
        reason=reason,
    )
    db.flush()
    return True


def verify_locked_place(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str | None = None,
    action: str = "verify_place",
    reject_noop: bool = False,
    verification_status: str = "verified",
    verification_source: str | None = None,
    verification_method: str | None = None,
) -> bool:
    if verification_status not in {"verified", "trusted"}:
        raise ValueError(f"unsupported successful verification status: {verification_status}")
    return transition_place_verification(
        db,
        place,
        to_status=verification_status,
        actor=actor,
        reason=reason,
        action=action,
        verification_source=verification_source,
        verification_method=verification_method,
        reject_noop=reject_noop,
    )


def reject_locked_place_verification(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str,
    action: str = "reject_place_verification",
) -> bool:
    return transition_place_verification(
        db,
        place,
        to_status="rejected",
        actor=actor,
        reason=reason,
        action=action,
        verification_source="admin_review",
        verification_method="manual_rejection",
    )
