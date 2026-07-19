"""Canonical non-committing mutation for the complete Place verification state."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from services.admin_audit_service import write_admin_audit_log

_ALLOWED_VERIFICATION_STATUSES = frozenset(
    {
        "unverified",
        "needs_recheck",
        "verified",
        "trusted",
        "rejected",
        "not_found",
        "closed",
        "moved",
        "duplicate",
    }
)


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
    confidence_score: int | None = None,
    confidence_level: str | None = None,
    set_verified_at: bool | None = None,
    reject_noop: bool = False,
    lock_place: bool = True,
) -> bool:
    """Apply verification state and audit it; never commit or change publication."""
    if not str(actor or "").strip():
        raise ValueError("verification actor is required")
    if to_status not in _ALLOWED_VERIFICATION_STATUSES:
        raise ValueError(f"unsupported verification status: {to_status}")
    if place.id is None:
        db.flush()
    if lock_place:
        place = (
            db.query(Place)
            .filter(Place.id == place.id)
            .populate_existing()
            .with_for_update()
            .one()
        )

    target_score, target_level, should_set_verified_at = _target_values(
        place,
        to_status=to_status,
        confidence_score=confidence_score,
        confidence_level=confidence_level,
        set_verified_at=set_verified_at,
    )
    target_verified_by = None if to_status == "unverified" else (
        place.verified_by if to_status == "needs_recheck" else actor
    )
    is_noop = (
        place.verification_status == to_status
        and place.existence_confidence_level == target_level
        and int(place.existence_confidence_score or 0) == target_score
        and place.verification_source == verification_source
        and place.verification_method == verification_method
        and place.verified_by == target_verified_by
    )
    if is_noop:
        if reject_noop:
            raise ValueError("Состояние проверки уже установлено")
        return False

    old_value = _snapshot(place)
    now = datetime.utcnow()
    place.verification_status = to_status
    place.verification_source = verification_source
    place.verification_method = verification_method
    place.existence_confidence_level = target_level
    place.existence_confidence_score = target_score
    place.verification_comment = reason

    if to_status == "needs_recheck":
        place.needs_recheck_at = now
        # Preserve the identity and timestamps of the last completed verification.
    elif to_status == "unverified":
        place.needs_recheck_at = None
        place.verified_at = None
        place.verified_by = None
        place.last_verified_at = None
    else:
        place.needs_recheck_at = None
        place.verified_by = actor
        if should_set_verified_at:
            place.verified_at = now
        place.last_verified_at = now

    place.updated_at = now
    write_admin_audit_log(
        db,
        actor=actor,
        action=action,
        entity_type="place",
        entity_id=place.id,
        old_value=old_value,
        new_value=_snapshot(place),
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
    lock_place: bool = True,
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
        confidence_score=max(place.existence_confidence_score or 0, 90),
        confidence_level="high",
        set_verified_at=True,
        reject_noop=reject_noop,
        lock_place=lock_place,
    )


def reject_locked_place_verification(
    db: Session,
    place: Place,
    *,
    actor: str,
    reason: str,
    action: str = "reject_place_verification",
    lock_place: bool = True,
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
        confidence_score=0,
        confidence_level="low",
        set_verified_at=True,
        lock_place=lock_place,
    )


def _target_values(
    place: Place,
    *,
    to_status: str,
    confidence_score: int | None,
    confidence_level: str | None,
    set_verified_at: bool | None,
) -> tuple[int, str, bool]:
    defaults: dict[str, tuple[int, str, bool]] = {
        "unverified": (0, "unknown", False),
        "needs_recheck": (min(int(place.existence_confidence_score or 0), 50), "low", False),
        "verified": (max(int(place.existence_confidence_score or 0), 90), "high", True),
        "trusted": (max(int(place.existence_confidence_score or 0), 90), "high", True),
        "rejected": (0, "low", True),
        "not_found": (15, "low", True),
        "closed": (0, "unknown", True),
        "moved": (40, "low", True),
        "duplicate": (0, "unknown", True),
    }
    default_score, default_level, default_verified = defaults[to_status]
    score = default_score if confidence_score is None else int(confidence_score)
    if score < 0 or score > 100:
        raise ValueError("verification confidence score must be between 0 and 100")
    level = confidence_level or default_level
    verified = default_verified if set_verified_at is None else bool(set_verified_at)
    return score, level, verified


def _snapshot(place: Place) -> dict[str, object]:
    return {
        "verification_status": place.verification_status,
        "verification_source": place.verification_source,
        "verification_method": place.verification_method,
        "existence_confidence_level": place.existence_confidence_level,
        "existence_confidence_score": place.existence_confidence_score,
        "verified_by": place.verified_by,
        "verified_at": place.verified_at.isoformat() if place.verified_at else None,
        "last_verified_at": place.last_verified_at.isoformat() if place.last_verified_at else None,
        "needs_recheck_at": place.needs_recheck_at.isoformat() if place.needs_recheck_at else None,
        "verification_comment": place.verification_comment,
    }
