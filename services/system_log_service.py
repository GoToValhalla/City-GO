"""Запись и чтение system logs."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from core.config import settings
from models.system_log import SystemLog


def write_system_log(
    db: Session,
    *,
    level: str,
    module: str,
    message: str,
    details: dict[str, Any] | None = None,
    city_slug: str | None = None,
    place_id: int | None = None,
    route_id: str | None = None,
    request_id: str | None = None,
    actor_id: str | None = None,
    commit: bool = True,
) -> SystemLog:
    row = SystemLog(
        level=level, module=module, message=message, details=details,
        city_slug=city_slug, place_id=place_id, route_id=route_id,
        request_id=request_id, actor_id=actor_id, environment=settings.app_env,
    )
    db.add(row)
    if commit:
        db.commit()
        db.refresh(row)
    return row


def list_system_logs(
    db: Session,
    *,
    level: str | None = None,
    module: str | None = None,
    city_slug: str | None = None,
    request_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[SystemLog], int]:
    query = db.query(SystemLog)
    if level:
        query = query.filter(SystemLog.level == level)
    if module:
        query = query.filter(SystemLog.module == module)
    if city_slug:
        query = query.filter(SystemLog.city_slug == city_slug)
    if request_id:
        query = query.filter(SystemLog.request_id == request_id)
    total = query.count()
    items = query.order_by(SystemLog.created_at.desc()).offset(offset).limit(limit).all()
    return items, total
