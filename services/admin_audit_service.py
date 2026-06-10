from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog


def write_admin_audit_log(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    reason: str | None = None,
) -> AdminAuditLog:
    log = AdminAuditLog(
        actor=actor or "admin",
        action=action,
        entity_type=entity_type,
        entity_id=None if entity_id is None else str(entity_id),
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(log)
    return log


def get_admin_audit_logs(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    entity_type: str | None = None,
    action: str | None = None,
    actor: str | None = None,
    entity_id: str | None = None,
) -> tuple[list[AdminAuditLog], int]:
    query = db.query(AdminAuditLog)
    if entity_type:
        query = query.filter(AdminAuditLog.entity_type == entity_type)
    if action:
        query = query.filter(AdminAuditLog.action == action)
    if actor:
        query = query.filter(AdminAuditLog.actor.ilike(f"%{actor.strip()}%"))
    if entity_id:
        query = query.filter(AdminAuditLog.entity_id == entity_id)
    total = query.count()
    items = query.order_by(AdminAuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return items, total
