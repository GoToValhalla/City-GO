import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.source_observation import SourceObservation


def create_source_observation(
    db: Session,
    batch_id: int,
    city_id: int,
    source_external_id: str,
    raw_payload: dict[str, object],
    scope_id: int | None = None,
    rejection_reason: str | None = None,
) -> SourceObservation:
    idempotency_key = f"{batch_id}:{source_external_id}"

    existing = (
        db.query(SourceObservation)
        .filter(SourceObservation.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        existing.raw_payload = raw_payload
        existing.payload_hash = _payload_hash(raw_payload)
        existing.rejection_reason = rejection_reason
        existing.match_status = "rejected" if rejection_reason else "new_source_object"
        existing.normalization_status = "rejected" if rejection_reason else "raw_only"
        existing.seen_in_batch_id = batch_id
        db.commit()
        db.refresh(existing)
        return existing

    item = SourceObservation(
        import_batch_id=batch_id,
        seen_in_batch_id=batch_id,
        city_id=city_id,
        scope_id=scope_id,
        source_external_id=source_external_id,
        raw_payload=raw_payload,
        payload_hash=_payload_hash(raw_payload),
        idempotency_key=idempotency_key,
        rejection_reason=rejection_reason,
        match_status="rejected" if rejection_reason else "new_source_object",
        normalization_status="rejected" if rejection_reason else "raw_only",
    )
    try:
        with db.begin_nested():
            db.add(item)
            db.flush()
    except IntegrityError:
        # A concurrent writer won the race for this idempotency_key; the
        # SAVEPOINT above is rolled back automatically, the outer
        # transaction is untouched.
        existing = (
            db.query(SourceObservation)
            .filter(SourceObservation.idempotency_key == idempotency_key)
            .first()
        )
        if existing is None:
            raise
        db.commit()
        return existing
    db.commit()
    db.refresh(item)
    return item


def _payload_hash(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
