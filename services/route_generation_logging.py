"""System logs и product events для генерации маршрутов."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from services.product_event_service import record_event
from services.system_log_service import write_system_log


def log_route_generation_started(
    db: Session,
    *,
    source: str,
    city_slug: str | None,
    user_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    record_event(
        db,
        event_type="route_generation_started",
        city_slug=city_slug,
        user_id=user_id,
        payload={"source": source, **(payload or {})},
    )


def log_route_generation_success(
    db: Session,
    *,
    source: str,
    city_slug: str | None,
    user_id: str | None = None,
    stops: int = 0,
    generation_run_id: int | None = None,
) -> None:
    record_event(
        db,
        event_type="route_generation_success",
        city_slug=city_slug,
        user_id=user_id,
        payload={"source": source, "stops": stops, "generation_run_id": generation_run_id},
    )


def log_route_generation_failed(
    db: Session,
    *,
    source: str,
    city_slug: str | None,
    reason: str,
    user_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    write_system_log(
        db,
        level="error",
        module="route_generation",
        message=reason,
        city_slug=city_slug,
        details={"source": source, **(details or {})},
    )
    record_event(
        db,
        event_type="route_generation_failed",
        city_slug=city_slug,
        user_id=user_id,
        payload={"source": source, "reason": reason},
    )


def log_admin_dry_run(
    db: Session,
    *,
    success: bool,
    city_slug: str | None,
    actor_id: str,
    generation_run_id: int | None = None,
    reason: str | None = None,
) -> None:
    event = "admin_route_dry_run_success" if success else "admin_route_dry_run_failed"
    record_event(
        db,
        event_type=event,
        city_slug=city_slug,
        payload={"actor_id": actor_id, "generation_run_id": generation_run_id, "reason": reason},
    )
    if not success and reason:
        write_system_log(
            db,
            level="warning",
            module="admin_route_dry_run",
            message=reason,
            city_slug=city_slug,
            actor_id=actor_id,
        )
