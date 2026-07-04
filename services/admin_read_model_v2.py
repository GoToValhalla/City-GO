from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.admin_read_snapshot import AdminOverviewSnapshot, BacklogQueueSnapshot

TTL_SECONDS = 300
SLOT_OVERVIEW = 1
SLOT_BACKLOG = 2
SLOT_PLAN = 3
SLOT_DATA_QUALITY = 4

Builder = Callable[[Session], dict[str, object]]


def admin_overview(db: Session) -> dict[str, object]:
    from services.admin_overview_compact import build_admin_overview

    return _read_or_build(db, SLOT_OVERVIEW, build_admin_overview)


def backlog_breakdown(db: Session) -> dict[str, object]:
    from services.admin_backlog_breakdown_service import _build_admin_backlog_breakdown_live

    return _read_or_build(db, SLOT_BACKLOG, _build_admin_backlog_breakdown_live)


def reduction_plan(db: Session) -> dict[str, object]:
    from services.admin_backlog_reduction_service import _build_reduction_plan_live

    return _read_or_build(db, SLOT_PLAN, _build_reduction_plan_live)


def data_quality_summary(db: Session) -> dict[str, object]:
    from services.data_quality.query import _build_data_quality_summary_live

    return _read_or_build(db, SLOT_DATA_QUALITY, _build_data_quality_summary_live)


def refresh_all(db: Session) -> dict[str, object]:
    from services.admin_backlog_breakdown_service import _build_admin_backlog_breakdown_live
    from services.admin_backlog_reduction_service import _build_reduction_plan_live
    from services.admin_overview_compact import build_admin_overview
    from services.data_quality.query import _build_data_quality_summary_live

    overview = build_admin_overview(db)
    backlog = _build_admin_backlog_breakdown_live(db)
    plan = _build_reduction_plan_live(db)
    quality = _build_data_quality_summary_live(db)
    _store(db, SLOT_OVERVIEW, "admin_overview", overview)
    _store(db, SLOT_BACKLOG, "backlog_breakdown", backlog)
    _store(db, SLOT_PLAN, "backlog_reduction_plan", plan)
    _store(db, SLOT_DATA_QUALITY, "data_quality_summary", quality)
    _store_queue_rows(db, backlog)
    db.commit()
    return {"status": "refreshed", "computed_at": datetime.utcnow().isoformat(), "snapshots": 4, "queues": len(backlog.get("queues") or [])}


def _read_or_build(db: Session, slot: int, builder: Builder) -> dict[str, object]:
    payload = _read(db, slot)
    if payload is not None:
        return payload
    return builder(db)


def _read(db: Session, slot: int) -> dict[str, object] | None:
    try:
        row = db.query(AdminOverviewSnapshot).filter(AdminOverviewSnapshot.id == slot).first()
        if row is None or row.is_dirty or not isinstance(row.payload, dict):
            return None
        if row.stale_after is not None and row.stale_after < datetime.utcnow():
            return None
        return dict(row.payload)
    except SQLAlchemyError:
        db.rollback()
        return None


def _store(db: Session, slot: int, source: str, payload: dict[str, object]) -> None:
    now = datetime.utcnow()
    row = db.query(AdminOverviewSnapshot).filter(AdminOverviewSnapshot.id == slot).first()
    if row is None:
        row = AdminOverviewSnapshot(id=slot)
        db.add(row)
    row.payload = _jsonable(payload)
    row.computed_at = now
    row.stale_after = now + timedelta(seconds=TTL_SECONDS)
    row.is_dirty = False
    row.source_version = source


def _store_queue_rows(db: Session, backlog: dict[str, object]) -> None:
    now = datetime.utcnow()
    stale_after = now + timedelta(seconds=TTL_SECONDS)
    for queue in backlog.get("queues") or []:
        if not isinstance(queue, dict):
            continue
        code = str(queue.get("code") or "")
        if not code:
            continue
        _queue_row(db, code, "__total__", int(queue.get("unique_places_count") or queue.get("total_count") or 0), now, stale_after)
        for reason in queue.get("reasons") or []:
            if isinstance(reason, dict) and reason.get("code"):
                _queue_row(db, code, str(reason.get("code")), int(reason.get("count") or 0), now, stale_after)


def _queue_row(db: Session, queue_code: str, reason_code: str, count: int, now: datetime, stale_after: datetime) -> None:
    row = db.query(BacklogQueueSnapshot).filter(
        BacklogQueueSnapshot.scope_type == "global",
        BacklogQueueSnapshot.scope_id == "global",
        BacklogQueueSnapshot.queue_code == queue_code,
        BacklogQueueSnapshot.reason_code == reason_code,
    ).first()
    if row is None:
        row = BacklogQueueSnapshot(scope_type="global", scope_id="global", queue_code=queue_code, reason_code=reason_code)
        db.add(row)
    row.count = count
    row.sample_place_ids = []
    row.computed_at = now
    row.stale_after = stale_after


def _jsonable(payload: dict[str, object]) -> dict[str, object]:
    return json.loads(json.dumps(payload, ensure_ascii=False, default=_json_default))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
