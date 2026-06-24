"""Запись и чтение system logs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import or_
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
    q: str | None = None,
    place_id: int | None = None,
    route_id: str | None = None,
    actor_id: str | None = None,
    environment: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort: str = "desc",
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
    if q:
        term = f"%{q.strip()}%"
        query = query.filter(or_(SystemLog.message.ilike(term), SystemLog.module.ilike(term)))
    if place_id is not None:
        query = query.filter(SystemLog.place_id == place_id)
    if route_id:
        query = query.filter(SystemLog.route_id == route_id)
    if actor_id:
        query = query.filter(SystemLog.actor_id == actor_id)
    if environment:
        query = query.filter(SystemLog.environment == environment)
    if created_from:
        query = query.filter(SystemLog.created_at >= created_from)
    if created_to:
        query = query.filter(SystemLog.created_at <= created_to)
    total = query.count()
    order = SystemLog.created_at.asc() if sort == "asc" else SystemLog.created_at.desc()
    items = query.order_by(order).offset(offset).limit(limit).all()
    return items, total
