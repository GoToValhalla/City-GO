from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog


def add_place_audit(db: Session, actor: str, action: str, place_id: int, old: object, new: object, reason: str | None) -> None:
    db.add(AdminAuditLog(actor=actor, action=action, entity_type="place", entity_id=str(place_id), old_value=json_safe(old), new_value=json_safe(new), reason=reason))


def json_safe(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    return value
