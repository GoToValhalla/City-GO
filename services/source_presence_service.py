from datetime import datetime

from sqlalchemy.orm import Session

from models.place_source_presence import PlaceSourcePresence


def mark_seen(db: Session, source_type: str, external_id: str, batch_id: int) -> PlaceSourcePresence:
    row = _get_or_create(db, source_type, external_id)
    now = datetime.utcnow()
    row.last_seen_at = now
    row.last_seen_batch_id = batch_id
    row.consecutive_missing_count = 0
    row.presence_status = "active_in_source"
    db.commit()
    db.refresh(row)
    return row


def mark_missing(db: Session, row: PlaceSourcePresence) -> PlaceSourcePresence:
    row.consecutive_missing_count += 1
    row.last_missing_at = datetime.utcnow()
    row.presence_status = _status(row.consecutive_missing_count)
    db.commit()
    db.refresh(row)
    return row


def _get_or_create(db: Session, source_type: str, external_id: str) -> PlaceSourcePresence:
    row = db.query(PlaceSourcePresence).filter_by(source_type=source_type, source_external_id=external_id).first()
    if row is not None:
        return row
    row = PlaceSourcePresence(source_type=source_type, source_external_id=external_id)
    db.add(row)
    return row


def _status(missing_count: int) -> str:
    if missing_count == 1:
        return "missing_once"
    return "possible_removed" if missing_count >= 3 else "missing_repeatedly"
