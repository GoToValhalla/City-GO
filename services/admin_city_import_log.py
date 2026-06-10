"""System logs для admin city import."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.system_log_service import write_system_log


def log_import_event(
    db: Session,
    *,
    event: str,
    city_slug: str,
    actor_id: str | None,
    level: str = "info",
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    write_system_log(
        db,
        level=level,
        module="city_import",
        message=message,
        details={"event": event, **(details or {})},
        city_slug=city_slug,
        actor_id=actor_id,
        commit=False,
    )
