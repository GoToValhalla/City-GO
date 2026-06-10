from datetime import datetime

from sqlalchemy.orm import Session

from models.city_scope_import_state import CityScopeImportState
from models.import_batch import ImportBatch


MAX_IMPORT_STATE_ERROR_LENGTH = 1000


def update_import_state(db: Session, batch: ImportBatch, status: str, error: str | None = None) -> CityScopeImportState:
    state = _get_or_create(db, batch)
    now = datetime.utcnow()
    state.last_attempted_batch_id = batch.id
    state.last_successful_batch_id = batch.id if status == "success" else state.last_successful_batch_id
    state.last_started_at = batch.started_at
    state.last_finished_at = now
    state.last_status = status
    state.last_error = _truncate_error(error)
    state.last_raw_count = batch.raw_count
    state.last_normalized_count = batch.normalized_count
    state.last_published_count = batch.published_count
    state.last_needs_review_count = batch.needs_review_count
    state.last_rejected_count = batch.rejected_count
    state.last_duplicate_count = batch.duplicate_count
    state.coverage_status = _coverage_status(status, batch)
    db.commit()
    db.refresh(state)
    return state


def _truncate_error(error: str | None) -> str | None:
    if error is None:
        return None

    if len(error) <= MAX_IMPORT_STATE_ERROR_LENGTH:
        return error

    return error[: MAX_IMPORT_STATE_ERROR_LENGTH - 3] + "..."


def _get_or_create(db: Session, batch: ImportBatch) -> CityScopeImportState:
    state = db.query(CityScopeImportState).filter_by(city_id=batch.city_id, scope_id=batch.scope_id).first()
    if state is not None:
        return state
    state = CityScopeImportState(city_id=batch.city_id, scope_id=batch.scope_id or 0)
    db.add(state)
    return state


def _coverage_status(status: str, batch: ImportBatch) -> str:
    if status != "success":
        return "failed"
    return "published" if batch.published_count else "needs_review"
