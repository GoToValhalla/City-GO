import hashlib
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from db.dependencies import get_db
from models.user_signal import UserSignal
from schemas.route_feedback import RouteFeedbackCreate, RouteFeedbackRead
from schemas.user_signal import SIGNAL_ROUTE_FEEDBACK
from services.anonymous_ownership import issue_ownership_token, optional_anonymous_session

router = APIRouter(prefix="/route-feedback", tags=["route-feedback"])

_DUPLICATE_WINDOW = timedelta(minutes=5)
_SIGNAL_TYPE = SIGNAL_ROUTE_FEEDBACK
_ENTITY_TYPE = "route"


def _dedup_subject(anonymous_subject: str | None, user_id: str | None) -> str:
    """Every independent caller must get its own identity for
    deduplication purposes. Priority: a real client-supplied identity
    (e.g. a Telegram user id) beats a hashed anonymous ownership token,
    which beats a fresh, single-use random id -- never a shared constant.
    Collapsing every unidentified caller into one shared string (the
    previous "anonymous" fallback) would let one anonymous submission
    suppress every other independent anonymous user's feedback for the
    same route within the dedup window, which is exactly the defect this
    replaces."""
    normalized_user_id = str(user_id or "").strip()
    if normalized_user_id:
        return normalized_user_id
    if anonymous_subject:
        return anonymous_subject
    return f"anon-request:{issue_ownership_token(nbytes=16)}"


def _dedup_key(*, subject: str, route_id: str, signal_payload: dict[str, object], now: datetime) -> str:
    """Deterministic fingerprint used as the atomic dedup boundary at the
    database level (see models/user_signal.py::UserSignal.dedup_key,
    a unique-indexed column). This is a fixed-bucket window, not a rolling
    one: bucket = floor(timestamp / window_seconds), so the window is
    aligned to fixed epoch-relative slots (e.g. every :00/:05/:10 minute
    mark for a 5-minute window), not to the time of the first submission.
    Two submissions with identical subject/route/payload collide only if
    they land in the same aligned bucket -- there is no read-then-write
    gap for a race to exploit within that bucket, regardless of which
    request's INSERT reaches the database first. Submissions that are only
    a few seconds apart but straddle a bucket boundary (e.g. one at :04:59
    and one at :05:01 for a 5-minute window) are NOT deduplicated against
    each other; only same-bucket duplicates are guaranteed to collide."""
    window_seconds = int(_DUPLICATE_WINDOW.total_seconds())
    bucket = int(now.timestamp()) // window_seconds
    fingerprint = "|".join([
        subject,
        _SIGNAL_TYPE,
        _ENTITY_TYPE,
        route_id,
        json.dumps(signal_payload, sort_keys=True, default=str),
        str(bucket),
    ])
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:64]


@router.post("/", response_model=RouteFeedbackRead)
def post_route_feedback(
    payload: RouteFeedbackCreate,
    anonymous_subject: str | None = Depends(optional_anonymous_session),
    db: Session = Depends(get_db),
) -> RouteFeedbackRead:
    """Сохраняет оценку маршрута как user signal для будущего обучения рекомендаций."""
    subject = _dedup_subject(anonymous_subject, payload.user_id)
    signal_payload: dict[str, object] = {
        "rating": payload.rating,
        "comment": payload.comment,
        "source": payload.source,
        "liked_place_ids": payload.liked_place_ids,
        "disliked_place_ids": payload.disliked_place_ids,
        "skipped_place_ids": payload.skipped_place_ids,
        "problem_types": payload.problem_types,
    }
    now = datetime.utcnow()
    dedup_key = _dedup_key(subject=subject, route_id=payload.route_id, signal_payload=signal_payload, now=now)

    values = {
        "user_id": subject,
        "signal_type": _SIGNAL_TYPE,
        "entity_type": _ENTITY_TYPE,
        "entity_id": payload.route_id,
        "payload": signal_payload,
        "dedup_key": dedup_key,
        "created_at": now,
    }
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        statement = pg_insert(UserSignal).values(**values).on_conflict_do_nothing(
            index_elements=[UserSignal.dedup_key]
        )
    elif dialect == "sqlite":
        statement = sqlite_insert(UserSignal).values(**values).on_conflict_do_nothing(
            index_elements=[UserSignal.dedup_key]
        )
    else:
        raise RuntimeError(f"Unsupported route-feedback database dialect: {dialect}")

    db.execute(statement)
    db.commit()

    signal = (
        db.query(UserSignal)
        .filter(UserSignal.dedup_key == dedup_key)
        .order_by(UserSignal.id.desc())
        .first()
    )
    return RouteFeedbackRead.model_validate(signal)
