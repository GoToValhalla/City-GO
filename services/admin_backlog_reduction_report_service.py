"""Operator report for backlog reduction runs and queued enrichment work."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.admin_operation import AdminOperation
from models.data_foundation import CityEnrichmentRun, EnrichmentTask

OPERATION_TYPE = "backlog_reduction"
RUN_TYPE = "backlog_reduction"
ACTIVE_TASK_STATUSES = ("queued", "running", "processing", "locked")
TASK_TYPES = ("photo_discovery", "address_recovery", "description_enrichment", "verification_recheck")


def build_backlog_reduction_report(db: Session) -> dict[str, Any]:
    now = datetime.utcnow()
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)
    operations = (
        db.query(AdminOperation)
        .filter(AdminOperation.operation_type == OPERATION_TYPE)
        .filter(AdminOperation.created_at >= since_7d)
        .order_by(AdminOperation.id.desc())
        .limit(1000)
        .all()
    )
    recent_runs = [_operation_payload(operation) for operation in operations[:10]]
    last_result = recent_runs[0] if recent_runs else None
    task_rows = (
        db.query(EnrichmentTask.task_type, EnrichmentTask.status, func.count(EnrichmentTask.id))
        .join(CityEnrichmentRun, EnrichmentTask.run_id == CityEnrichmentRun.id)
        .filter(CityEnrichmentRun.run_type == RUN_TYPE)
        .group_by(EnrichmentTask.task_type, EnrichmentTask.status)
        .all()
    )
    task_stats = _task_stats(task_rows)
    task_created_24h = _task_created_count(db, since_24h)
    task_created_7d = _task_created_count(db, since_7d)
    return {
        "generated_at": now,
        "summary": {
            "runs_24h": _run_count(operations, since_24h),
            "runs_7d": len(operations),
            "queued_24h": _sum_count(operations, since_24h, "queued_count"),
            "queued_7d": _sum_count(operations, since_7d, "queued_count"),
            "skipped_24h": _sum_count(operations, since_24h, "skipped_count"),
            "skipped_7d": _sum_count(operations, since_7d, "skipped_count"),
            "failed_24h": _sum_count(operations, since_24h, "failed_count"),
            "failed_7d": _sum_count(operations, since_7d, "failed_count"),
            "tasks_created_24h": task_created_24h,
            "tasks_created_7d": task_created_7d,
            "active_tasks": sum(int(row["active_count"]) for row in task_stats),
        },
        "last_result": last_result,
        "task_stats": task_stats,
        "recent_runs": recent_runs,
        "windows": {"last_24h_since": since_24h, "last_7d_since": since_7d},
    }


def _operation_payload(operation: AdminOperation) -> dict[str, Any]:
    result = operation.result or {}
    return {
        "job_id": operation.id,
        "status": operation.status,
        "action_code": result.get("action_code"),
        "actor": operation.actor,
        "started_at": operation.created_at,
        "finished_at": operation.updated_at,
        "limit": _to_int(result.get("limit")),
        "affected_count": _to_int(result.get("affected_count")),
        "changed_count": _to_int(result.get("changed_count")),
        "queued_count": _to_int(result.get("queued_count")),
        "skipped_count": _to_int(result.get("skipped_count")),
        "failed_count": _to_int(result.get("failed_count")),
        "skipped_reasons": result.get("skipped_reasons") or {},
        "message": result.get("message"),
    }


def _task_stats(rows: list[tuple[str, str, int]]) -> list[dict[str, Any]]:
    by_type: dict[str, dict[str, Any]] = {
        task_type: {"task_type": task_type, "total_count": 0, "active_count": 0, "statuses": {}}
        for task_type in TASK_TYPES
    }
    for task_type, status, count in rows:
        bucket = by_type.setdefault(task_type, {"task_type": task_type, "total_count": 0, "active_count": 0, "statuses": {}})
        count_int = _to_int(count)
        bucket["total_count"] += count_int
        bucket["statuses"][status] = count_int
        if status in ACTIVE_TASK_STATUSES:
            bucket["active_count"] += count_int
    return list(by_type.values())


def _task_created_count(db: Session, since: datetime) -> int:
    return _to_int(
        db.query(func.count(EnrichmentTask.id))
        .join(CityEnrichmentRun, EnrichmentTask.run_id == CityEnrichmentRun.id)
        .filter(CityEnrichmentRun.run_type == RUN_TYPE)
        .filter(EnrichmentTask.created_at >= since)
        .scalar()
    )


def _run_count(operations: list[AdminOperation], since: datetime) -> int:
    return sum(1 for operation in operations if operation.created_at >= since)


def _sum_count(operations: list[AdminOperation], since: datetime, field: str) -> int:
    return sum(_to_int((operation.result or {}).get(field)) for operation in operations if operation.created_at >= since)


def _to_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
