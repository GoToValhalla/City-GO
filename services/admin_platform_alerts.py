"""Operational alert projection and lifecycle."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.admin_alert import AdminAlert
from models.system_log import SystemLog
from services.admin_audit_service import write_admin_audit_log


def list_alerts(db: Session, *, status: str | None = None, limit: int = 50) -> list[dict[str, object]]:
    since = datetime.utcnow() - timedelta(days=14)
    logs = db.query(SystemLog).filter(
        SystemLog.level.in_(("error", "critical")), SystemLog.created_at >= since,
    ).order_by(SystemLog.created_at.desc()).limit(limit).all()
    states = {row.source_log_id: row for row in db.query(AdminAlert).filter(
        AdminAlert.source_log_id.in_([log.id for log in logs])
    ).all()} if logs else {}
    rows = [_payload(log, states.get(log.id)) for log in logs]
    return [row for row in rows if not status or row["status"] == status]


def transition_alert(db: Session, log_id: int, *, status: str, actor: str) -> dict[str, object] | None:
    log = db.query(SystemLog).filter(SystemLog.id == log_id).first()
    if log is None:
        return None
    row = db.query(AdminAlert).filter(AdminAlert.source_log_id == log_id).first()
    if row is None:
        row = AdminAlert(source_log_id=log_id, status="open")
        db.add(row)
    now = datetime.utcnow()
    row.status = status
    if status == "acknowledged":
        row.acknowledged_by, row.acknowledged_at = actor, now
    if status == "resolved":
        row.resolved_by, row.resolved_at = actor, now
    write_admin_audit_log(db, actor=actor, action=f"{status}_alert", entity_type="system_log", entity_id=log_id)
    db.commit()
    return _payload(log, row)


def _payload(log: SystemLog, state: AdminAlert | None) -> dict[str, object]:
    return {
        "id": log.id, "severity": log.level, "status": state.status if state else "open",
        "module": log.module, "message": log.message, "city_slug": log.city_slug,
        "request_id": log.request_id, "created_at": log.created_at,
    }
