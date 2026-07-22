from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from models.user_signal import UserSignal
from schemas.route_feedback import RouteFeedbackCreate, RouteFeedbackRead
from schemas.user_signal import SIGNAL_ROUTE_FEEDBACK
from services.anonymous_ownership import issue_ownership_token

_DUPLICATE_WINDOW = timedelta(minutes=5)
_SIGNAL_TYPE = SIGNAL_ROUTE_FEEDBACK
_ENTITY_TYPE = "route"


def dedup_subject(anonymous_subject: str | None, user_id: str | None) -> str:
    """Keep independent anonymous callers distinct; never use a shared fallback identity."""

    normalized = str(user_id or "").strip()
    return normalized or anonymous_subject or f"anon-request:{issue_ownership_token(nbytes=16)}"


def dedup_key(*, subject: str, route_id: str, signal_payload: dict[str, object], now: datetime) -> str:
    """Fingerprint one fixed epoch-aligned five-minute bucket, not a rolling window."""

    bucket = int(now.timestamp()) // int(_DUPLICATE_WINDOW.total_seconds())
    fingerprint = "|".join((
        subject, _SIGNAL_TYPE, _ENTITY_TYPE, route_id,
        json.dumps(signal_payload, sort_keys=True, default=str), str(bucket),
    ))
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:64]


def submit_route_feedback(
    db: Session, payload: RouteFeedbackCreate, *, anonymous_subject: str | None,
) -> RouteFeedbackRead:
    subject = dedup_subject(anonymous_subject, payload.user_id)
    signal_payload: dict[str, object] = {
        "rating": payload.rating, "comment": payload.comment, "source": payload.source,
        "liked_place_ids": payload.liked_place_ids, "disliked_place_ids": payload.disliked_place_ids,
        "skipped_place_ids": payload.skipped_place_ids, "problem_types": payload.problem_types,
    }
    now = datetime.utcnow()
    key = dedup_key(subject=subject, route_id=payload.route_id, signal_payload=signal_payload, now=now)
    values = {
        "user_id": subject, "signal_type": _SIGNAL_TYPE, "entity_type": _ENTITY_TYPE,
        "entity_id": payload.route_id, "payload": signal_payload, "dedup_key": key, "created_at": now,
    }
    statement = _insert(db, values).on_conflict_do_nothing(index_elements=[UserSignal.dedup_key])
    db.execute(statement)
    db.commit()
    signal = db.query(UserSignal).filter(UserSignal.dedup_key == key).order_by(UserSignal.id.desc()).first()
    return RouteFeedbackRead.model_validate(signal)


def _insert(db: Session, values: dict[str, object]):
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        return pg_insert(UserSignal).values(**values)
    if dialect == "sqlite":
        return sqlite_insert(UserSignal).values(**values)
    raise RuntimeError(f"Unsupported route-feedback database dialect: {dialect}")
