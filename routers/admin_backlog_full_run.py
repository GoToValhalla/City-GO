from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.admin_auth import AdminContext, admin_required
from db.dependencies import get_db
from services.admin_backlog_full_run_state import (
    complete_full_run,
    create_full_run,
    latest_full_run,
    mark_step_running,
    mark_stop_requested,
    read_full_run,
    record_step_error,
    record_step_result,
)

router = APIRouter(prefix="/admin/overview/backlog-reduction/full-safe-run", tags=["admin-ops"])


class FullRunStepResult(BaseModel):
    status: str = "completed"
    affected_count: int = 0
    changed_count: int = 0
    queued_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    message: str | None = None
    job_id: int | None = None
    audit_id: int | None = None


class FullRunStepError(BaseModel):
    message: str


@router.post("")
def create_admin_backlog_full_run(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    return create_full_run(db, actor=auth.actor_id)


@router.get("/latest")
def read_latest_admin_backlog_full_run(auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object] | None:
    return latest_full_run(db)


@router.get("/{job_id}")
def read_admin_backlog_full_run(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    payload = read_full_run(db, job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return payload


@router.post("/{job_id}/stop")
def stop_admin_backlog_full_run(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    payload = mark_stop_requested(db, job_id, actor=auth.actor_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return payload


@router.post("/{job_id}/steps/{action_code}/running")
def mark_admin_backlog_full_run_step_running(job_id: int, action_code: str, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    payload = mark_step_running(db, job_id, action_code)
    if payload is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return payload


@router.post("/{job_id}/steps/{action_code}/result")
def record_admin_backlog_full_run_step_result(job_id: int, action_code: str, payload: FullRunStepResult, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    result = record_step_result(db, job_id, action_code, payload.model_dump())
    if result is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return result


@router.post("/{job_id}/steps/{action_code}/error")
def record_admin_backlog_full_run_step_error(job_id: int, action_code: str, payload: FullRunStepError, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    result = record_step_error(db, job_id, action_code, payload.message)
    if result is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return result


@router.post("/{job_id}/complete")
def complete_admin_backlog_full_run(job_id: int, auth: AdminContext = Depends(admin_required), db: Session = Depends(get_db)) -> dict[str, object]:
    result = complete_full_run(db, job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Полный прогон не найден.")
    return result
