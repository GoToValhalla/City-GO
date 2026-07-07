"""Transaction boundaries for import pipeline steps."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from services.import_pipeline.schema_compat import is_schema_mismatch_error


def is_aborted_transaction_error(exc: BaseException) -> bool:
    text_value = str(exc).lower()
    return "infailedsqltransaction" in text_value or "current transaction is aborted" in text_value


def rollback_session(db: Session) -> bool:
    try:
        db.rollback()
        return True
    except SQLAlchemyError:
        return False


def transaction_is_aborted(db: Session) -> bool:
    try:
        db.connection().execute(text("SELECT 1"))
        return False
    except SQLAlchemyError as exc:
        return is_aborted_transaction_error(exc)


def rollback_if_aborted(db: Session) -> bool:
    if not transaction_is_aborted(db):
        return False
    return rollback_session(db)


def verify_session_usable(db: Session) -> bool:
    try:
        db.connection().execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        if not rollback_session(db):
            return False
        try:
            db.connection().execute(text("SELECT 1"))
            return True
        except SQLAlchemyError:
            return False


def record_step_isolation(
    db: Session,
    job: CityAdminImportJob,
    *,
    after_step: str,
    reason: str,
    dependency: str | None = None,
    force: bool = False,
) -> dict[str, object]:
    rolled_back = rollback_if_aborted(db) if not force else rollback_session(db)
    payload: dict[str, object] = {
        "step": "transaction_isolation",
        "status": "rolled_back" if rolled_back else "not_required",
        "after_step": after_step,
        "reason": reason,
    }
    if dependency is not None:
        payload["dependency"] = dependency
    return payload


def recover_after_db_error(db: Session, job: CityAdminImportJob, *, step: str, error: BaseException | None = None) -> dict[str, object]:
    should_rollback = (
        error is None
        or isinstance(error, SQLAlchemyError)
        or is_aborted_transaction_error(error)
        or is_schema_mismatch_error(error)
        or transaction_is_aborted(db)
    )
    rolled_back = rollback_session(db) if should_rollback else False
    usable = verify_session_usable(db)
    isolation = record_step_isolation(
        db,
        job,
        after_step=step,
        reason="db_error_recovered",
        force=should_rollback,
    )
    return {**isolation, "rolled_back": rolled_back, "session_usable": usable, "error": str(error)[:1000] if error else None}
