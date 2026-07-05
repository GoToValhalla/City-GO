from __future__ import annotations

import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from db.session import SessionLocal
from schemas.admin_backlog_reduction import BacklogReductionApplyRequest
from services.admin_backlog_full_run_state import (
    SAFE_QUEUE_ACTIONS,
    complete_full_run,
    finalize_stopped,
    mark_step_running,
    read_full_run,
    record_step_error,
    record_step_result,
    should_stop,
)
from services.admin_backlog_reduction_service import apply as apply_backlog_reduction

logger = logging.getLogger(__name__)
FULL_SAFE_REDUCTION_LIMIT = 500


def run_full_safe_backlog_reduction(job_id: int, *, actor: str = "admin") -> None:
    """Run the full safe backlog reduction on the backend, not in the browser.

    The function is intended for FastAPI BackgroundTasks. It uses its own DB session,
    persists progress after each step, and checks stop_requested before every next action.
    """
    db = SessionLocal()
    try:
        for action_code in SAFE_QUEUE_ACTIONS:
            current = read_full_run(db, job_id)
            if current is None:
                logger.warning("full safe backlog run %s disappeared before %s", job_id, action_code)
                return
            if should_stop(db, job_id):
                finalize_stopped(db, job_id)
                return

            mark_step_running(db, job_id, action_code)
            try:
                result = apply_backlog_reduction(
                    db,
                    BacklogReductionApplyRequest(
                        action_code=action_code,
                        confirmation_text="APPLY",
                        limit=FULL_SAFE_REDUCTION_LIMIT,
                        include_samples=True,
                    ),
                    actor=actor or "admin",
                )
                record_step_result(db, job_id, action_code, result.model_dump(mode="json"))
            except HTTPException as exc:
                db.rollback()
                detail = str(exc.detail or exc)
                logger.exception("full safe backlog run %s action %s failed: %s", job_id, action_code, detail)
                record_step_error(db, job_id, action_code, detail)
            except (SQLAlchemyError, TimeoutError) as exc:
                db.rollback()
                logger.exception("full safe backlog run %s action %s db failure", job_id, action_code)
                record_step_error(db, job_id, action_code, str(exc))
            except Exception as exc:  # noqa: BLE001 - keep the persistent job from dying silently.
                db.rollback()
                logger.exception("full safe backlog run %s action %s unexpected failure", job_id, action_code)
                record_step_error(db, job_id, action_code, str(exc))

            if should_stop(db, job_id):
                finalize_stopped(db, job_id)
                return

        if should_stop(db, job_id):
            finalize_stopped(db, job_id)
            return
        complete_full_run(db, job_id)
    except Exception:  # noqa: BLE001 - final guard, state is best-effort persisted above.
        db.rollback()
        logger.exception("full safe backlog run %s fatal failure", job_id)
    finally:
        db.close()
