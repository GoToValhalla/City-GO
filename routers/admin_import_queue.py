from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_tasks import run_queued_import_jobs
from services.import_pipeline.steps import STEP_ERROR

router = APIRouter(prefix="/admin", tags=["admin-import-queue"])

MAX_RUNNING_SECONDS = 60 * 60


def _utc_naive(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _running_seconds(job: CityAdminImportJob, *, now: datetime) -> int | None:
    now_value = _utc_naive(now) or datetime.utcnow()
    ref = _utc_naive(job.started_at or job.updated_at or job.created_at)
    if ref is None:
        return None
    return max(0, int((now_value - ref).total_seconds()))


def _is_stuck(job: CityAdminImportJob, *, now: datetime) -> bool:
    seconds = _running_seconds(job, now=now)
    return job.status == "running" and seconds is not None and seconds > MAX_RUNNING_SECONDS


def _summary(db: Session) -> dict[str, Any]:
    now = datetime.utcnow()
    total = db.query(CityAdminImportJob.id).count()
    active = db.query(CityAdminImportJob).filter(CityAdminImportJob.status.in_(("queued", "running"))).all()
    queued = [job for job in active if job.status == "queued"]
    running = [job for job in active if job.status == "running"]
    stuck = [job for job in running if _is_stuck(job, now=now)]
    oldest_queued_seconds = None
    if queued:
        oldest = min((_utc_naive(job.created_at) for job in queued if job.created_at), default=None)
        if oldest is not None:
            oldest_queued_seconds = int((now - oldest).total_seconds())
    running_seconds = [_running_seconds(job, now=now) or 0 for job in running]
    return {
        "total": total,
        "active_total": len(active),
        "queued": len(queued),
        "running": len(running),
        "stalled_running": len(stuck),
        "oldest_queued_seconds": oldest_queued_seconds,
        "longest_running_seconds": max(running_seconds, default=None),
        "running_job_ids": [job.id for job in running],
        "stale_job_ids": [job.id for job in stuck],
        "next_job_ids": [job.id for job in sorted(queued, key=lambda item: (_utc_naive(item.created_at) or datetime.min, item.id))[:10]],
        "by_status": dict(Counter(str(job.status or "unknown") for job in active)),
        "by_source": dict(Counter(str(job.source or "unknown") for job in active)),
    }


@router.get("/import-queue")
def read_import_queue(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    return _summary(db)


@router.post("/import-queue/run-once")
def run_import_queue_once(background_tasks: BackgroundTasks, limit: int = 1, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    """Manually kick the import worker without enabling the web startup scheduler."""
    worker_limit = max(1, min(int(limit or 1), 5))
    background_tasks.add_task(run_queued_import_jobs, actor_id=auth.actor_id, limit=worker_limit)
    return {"scheduled": True, "limit": worker_limit, "queue": _summary(db)}


@router.post("/import-queue/mark-stalled")
def mark_stuck_import_jobs(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    now = datetime.utcnow()
    jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").all()
    stuck = [job for job in jobs if _is_stuck(job, now=now)]
    marked: list[int] = []
    for job in stuck:
        city = db.query(City).filter(City.id == job.city_id).first()
        details = dict(job.step_details or {})
        details["manual_stalled_recovery"] = {
            "marked_at": now.isoformat(),
            "actor_id": auth.actor_id,
            "running_seconds": _running_seconds(job, now=now),
        }
        job.step_details = details
        job.status = "stalled"
        job.current_step = STEP_ERROR
        job.last_error = job.last_error or "Import job manually marked as stalled after exceeding runtime timeout"
        job.finished_at = now
        job.updated_at = now
        if city is not None and city.launch_status != "published":
            city.launch_status = "import_failed"
            city.is_active = False
        marked.append(int(job.id))
    if marked:
        db.commit()
        send_admin_alert(
            title="Import queue recovered stuck jobs",
            message=f"Marked stalled import jobs: {', '.join(map(str, marked))}",
            level="warning",
            details={"marked_job_ids": marked, "actor_id": auth.actor_id},
        )
    return {"marked": len(marked), "job_ids": marked, "queue": _summary(db)}
