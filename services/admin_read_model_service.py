"""Admin read-model snapshots with safe live fallback.

The request path reads prepared snapshots when they exist and are fresh. A
separate refresh call/job computes and stores snapshots. If tables are missing
or stale, endpoints fall back to the current live builders so deployment remains
backward compatible during migration rollout.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Callable

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.admin_read_snapshot import AdminOverviewSnapshot, BacklogQueueSnapshot

SNAPSHOT_TTL_SECONDS = 300
OVERVIEW_SLOT = 1
BACKLOG_SLOT = 2
REDUCTION_PLAN_SLOT = 3
DATA_QUALITY_SLOT = 4
GLOBAL_SCOPE = "global"

PayloadBuilder = Callable[[Session], dict[str, object]]


def get_admin_overview_read_model(db: Session) -> dict[str, object]:
    from services.admin_overview_compact import build_admin_overview

    return _get_or_live(db, OVERVIEW_SLOT, build_admin_overview)


def get_admin_backlog_breakdown_read_model(db: Session) -> dict[str, object]:
    from services.admin_backlog_breakdown_service import build_admin_backlog_breakdown

    return _get_or_live(db, BACKLOG_SLOT, build_admin_backlog_breakdown)


def get_admin_reduction_plan_read_model(db: Session) -> dict[str, object]:
    from services.admin_backlog_reduction_service import build_reduction_plan

    return _get_or_live(db, REDUCTION_PLAN_SLOT, build_reduction_plan)


def get_data_quality_summary_read_model(db: Session) -> dict[str, object]:
    from services.data_quality.query import build_data_quality_summary

    return _get_or_live(db, DATA_QUALITY_SLOT, build_data_quality_summary)


def refresh_all_admin_read_models(db: Session) -> dict[str, object]:
    from services.admin_backlog_breakdown_service import build_admin_backlog_breakdown
    from services.admin_backlog_reduction_service import build_reduction_plan
    from services.admin_overview_compact import build_admin_overview
    from services.data_quality.query import build_data_quality_summary

    overview = build_admin_overview(db)
    backlog = build_admin_backlog_breakdown(db)
    reduction_plan = build_reduction_plan(db)
    data_quality = build_data_quality_summary(db)

    _write_snapshot(db, OVERVIEW_SLOT, "admin_overview", overview)
    _write_snapshot(db, BACKLOG_SLOT, "backlog_breakdown", backlog)
    _write_snapshot(db, REDUCTION_PLAN_SLOT, "backlog_reduction_plan", reduction_plan)
    _write_snapshot(db, DATA_QUALITY_SLOT, "data_quality_summary", data_quality)
    _write_backlog_queue_snapshots(db, backlog)
    db.commit()

    return {
        "status": "refreshed",
        "computed_at": datetime.utcnow().isoformat(),
        "snapshots": ["admin_overview", "backlog_breakdown", "backlog_reduction_plan", "data_quality_summary", "backlog_queue_snapshot"],
        "backlog_queues": len(backlog.get("queues") or []),
    }


def _get_or_live(db: Session, slot: int, builder: PayloadBuilder) -> dict[str, object]:
    payload = _read_snapshot(db, slot)
    if payload is not None:
        return payload
    return builder(db)


def _read_snapshot(db: Session, slot: int) -> dict[str, object] | None:
    try:
        row = db.query(AdminOverviewSnapshot).filter(AdminOverviewSnapshot.id == slot).first()
        if row is None or row.is_dirty:
            return None
        now = datetime.utcnow()
        if row.stale_after is not None and row.stale_after < now:
            return None
        if not isinstance(row.payload, dict):
            return None
        return dict(row.payload)
    except SQLAlchemyError:
        db.rollback()
        return None


def _write_snapshot(db: Session, slot: int, source_version: str, payload: dict[str, object]) -> None:
    now = datetime.utcnow()
    row = db.query(AdminOverviewSnapshot).filter(AdminOverviewSnapshot.id == slot).first()
    if row is None:
        row = AdminOverviewSnapshot(id=slot)
        db.add(row)
    row.payload = _jsonable(payload)
    row.computed_at = now
    row.stale_after = now + timedelta(seconds=SNAPSHOT_TTL_SECONDS)
    row.is_dirty = False
    row.source_version = source_version


def _write_backlog_queue_snapshots(db: Session, backlog: dict[str, object]) -> None:
    now = datetime.utcnow()
    stale_after = now + timedelta(seconds=SNAPSHOT_TTL_SECONDS)
    for queue in backlog.get("queues") or []:
        if not isinstance(queue, dict):
            continue
        queue_code = str(queue.get("code") or "")
        if not queue_code:
            continue
        _upsert_queue_snapshot(db, queue_code=queue_code, reason_code="__total__", count=int(queue.get("unique_places_count") or queue.get("total_count") or 0), now=now, stale_after=stale_after)
        for reason in queue.get("reasons") or []:
            if not isinstance(reason, dict):
                continue
            reason_code = str(reason.get("code") or "")
            if not reason_code:
                continue
            _upsert_queue_snapshot(db, queue_code=queue_code, reason_code=reason_code, count=int(reason.get("count") or 0), now=now, stale_after=stale_after)


def _upsert_queue_snapshot(db: Session, *, queue_code: str, reason_code: str, count: int, now: datetime, stale_after: datetime) -> None:
    row = db.query(BacklogQueueSnapshot).filter(
        BacklogQueueSnapshot.scope_type == GLOBAL_SCOPE,
        BacklogQueueSnapshot.scope_id == GLOBAL_SCOPE,
        BacklogQueueSnapshot.queue_code == queue_code,
        BacklogQueueSnapshot.reason_code == reason_code,
    ).first()
    if row is None:
        row = BacklogQueueSnapshot(scope_type=GLOBAL_SCOPE, scope_id=GLOBAL_SCOPE, queue_code=queue_code, reason_code=reason_code)
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
