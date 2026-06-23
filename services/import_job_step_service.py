"""Persistence helpers for normalized import job steps."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.import_job_step import ImportJobStep


def record_step(
    db: Session,
    *,
    job_id: int,
    step_name: str,
    status: str,
    counters: dict[str, object] | None = None,
    error_message: str | None = None,
) -> ImportJobStep:
    step = _active_step(db, job_id, step_name) if status != "started" else None
    step = step or ImportJobStep(job_id=job_id, step_name=step_name, started_at=datetime.utcnow())
    step.status = status
    step.counters = counters or {}
    step.error_message = error_message
    step.finished_at = datetime.utcnow() if status in {"success", "failed", "warning"} else None
    db.add(step)
    return step


def _active_step(db: Session, job_id: int, step_name: str) -> ImportJobStep | None:
    return (
        db.query(ImportJobStep)
        .filter(ImportJobStep.job_id == job_id, ImportJobStep.step_name == step_name, ImportJobStep.finished_at.is_(None))
        .order_by(ImportJobStep.id.desc())
        .first()
    )


def list_job_steps(db: Session, job_id: int) -> list[ImportJobStep]:
    return (
        db.query(ImportJobStep)
        .filter(ImportJobStep.job_id == job_id)
        .order_by(ImportJobStep.id.asc())
        .all()
    )
