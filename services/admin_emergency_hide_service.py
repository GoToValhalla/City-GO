from __future__ import annotations

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.place import Place
from services.publication_state_writer import REASON_ADMIN_HIDE, transition_place_publication

EMERGENCY_HIDE_ACTION = "emergency_hide_place"


def emergency_hide_place(
    db: Session,
    *,
    place_id: int,
    actor: str,
    reason: str,
    idempotency_key: str,
) -> tuple[Place, AdminAuditLog, bool]:
    """Hide a place through the canonical writer with idempotent audit lineage."""

    normalized_reason = (reason or "").strip()
    if len(normalized_reason) < 10:
        raise ValueError("Укажите причину экстренного скрытия минимум 10 символов")
    normalized_key = (idempotency_key or "").strip()
    if len(normalized_key) < 8:
        raise ValueError("Укажите корректный ключ идемпотентности")

    place = (
        db.query(Place)
        .filter(Place.id == place_id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )
    if place is None:
        raise LookupError("Место не найдено")

    existing = (
        db.query(AdminAuditLog)
        .filter(
            AdminAuditLog.action == EMERGENCY_HIDE_ACTION,
            AdminAuditLog.entity_type == "place",
            AdminAuditLog.entity_id == str(place_id),
            AdminAuditLog.reason == normalized_key,
        )
        .one_or_none()
    )
    if existing is not None:
        return place, existing, True

    old_value = {
        "status": place.status,
        "publication_status": place.publication_status,
        "publication_reason_code": place.publication_reason_code,
        "is_published": place.is_published,
        "is_visible_in_catalog": place.is_visible_in_catalog,
        "is_route_eligible": place.is_route_eligible,
        "publication_comment": place.publication_comment,
    }

    try:
        transition_place_publication(
            db,
            place,
            to_status="hidden",
            reason_code=REASON_ADMIN_HIDE,
            actor=actor,
            source="admin_emergency_hide",
            reason_details={
                "incident_reason": normalized_reason,
                "idempotency_key": normalized_key,
            },
            human_comment=f"Экстренно скрыто: {normalized_reason}",
            correlation_id=normalized_key,
            lock_place=False,
        )
        place.status = "hidden"

        audit = AdminAuditLog(
            actor=actor,
            action=EMERGENCY_HIDE_ACTION,
            entity_type="place",
            entity_id=str(place_id),
            old_value=old_value,
            new_value={
                "status": place.status,
                "publication_status": place.publication_status,
                "publication_reason_code": place.publication_reason_code,
                "is_published": place.is_published,
                "is_visible_in_catalog": place.is_visible_in_catalog,
                "is_route_eligible": place.is_route_eligible,
                "idempotency_key": normalized_key,
                "comment": normalized_reason,
            },
            reason=normalized_key,
        )
        db.add(audit)
        db.commit()
        db.refresh(place)
        db.refresh(audit)
        return place, audit, False
    except Exception:
        db.rollback()
        raise
