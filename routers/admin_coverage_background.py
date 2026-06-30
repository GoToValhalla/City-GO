"""Background-first coverage refresh/status routes.

This router is registered before the legacy coverage-gaps router so POST /refresh
and /sync no longer run heavy assurance synchronously in the browser request.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from models.known_missing_poi import KnownMissingPoi
from services.admin_background_operation_service import (
    OP_COVERAGE_GAPS_REFRESH,
    create_background_operation,
    latest_operation,
    operation_payload,
    run_background_operation,
    snapshot_status_payload,
)

router = APIRouter(prefix="/admin/coverage-gaps", tags=["admin-coverage-gaps-background"])


@router.post("/refresh")
def queue_coverage_refresh(
    background_tasks: BackgroundTasks,
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _queue(db, background_tasks, actor=auth.actor_id, city_slug=city_slug)


@router.post("/sync")
def queue_coverage_sync(
    background_tasks: BackgroundTasks,
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return _queue(db, background_tasks, actor=auth.actor_id, city_slug=city_slug)


@router.get("/status")
def read_coverage_refresh_status(
    city_slug: str | None = Query(default=None),
    auth: AdminContext = Depends(admin_required),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    latest = latest_operation(db, operation_type=OP_COVERAGE_GAPS_REFRESH, city_slug=city_slug)
    snapshot = snapshot_status_payload(last_snapshot_at=_last_snapshot_at(db, city_slug=city_slug), latest=latest)
    return {"operation_type": OP_COVERAGE_GAPS_REFRESH, "city_slug": city_slug, **snapshot}


def _queue(
    db: Session,
    background_tasks: BackgroundTasks,
    *,
    actor: str,
    city_slug: str | None,
) -> dict[str, object]:
    op = create_background_operation(
        db,
        operation_type=OP_COVERAGE_GAPS_REFRESH,
        actor=actor,
        city_slug=city_slug,
        params={"city_slug": city_slug} if city_slug else {},
    )
    if op.status == "queued":
        background_tasks.add_task(run_background_operation, op.id)
    return operation_payload(op) or {}


def _last_snapshot_at(db: Session, *, city_slug: str | None) -> datetime | None:
    query = db.query(func.max(KnownMissingPoi.last_checked_at)).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    return query.scalar()
