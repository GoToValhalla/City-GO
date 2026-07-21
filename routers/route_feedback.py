from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from models.user_signal import UserSignal
from schemas.route_feedback import RouteFeedbackCreate, RouteFeedbackRead
from services.anonymous_ownership import optional_anonymous_session

router = APIRouter(prefix="/route-feedback", tags=["route-feedback"])

_DUPLICATE_WINDOW = timedelta(minutes=5)


@router.post("/", response_model=RouteFeedbackRead)
def post_route_feedback(
    payload: RouteFeedbackCreate,
    anonymous_subject: str | None = Depends(optional_anonymous_session),
    db: Session = Depends(get_db),
) -> RouteFeedbackRead:
    """Сохраняет оценку маршрута как user signal для будущего обучения рекомендаций."""
    subject = anonymous_subject or "anonymous"
    signal_payload: dict[str, object] = {
        "rating": payload.rating,
        "comment": payload.comment,
        "source": payload.source,
        "liked_place_ids": payload.liked_place_ids,
        "disliked_place_ids": payload.disliked_place_ids,
        "skipped_place_ids": payload.skipped_place_ids,
        "problem_types": payload.problem_types,
    }

    latest = (
        db.query(UserSignal)
        .filter(
            UserSignal.user_id == subject,
            UserSignal.signal_type == "route_feedback",
            UserSignal.entity_type == "route",
            UserSignal.entity_id == payload.route_id,
        )
        .order_by(UserSignal.created_at.desc(), UserSignal.id.desc())
        .first()
    )
    if (
        latest is not None
        and latest.payload == signal_payload
        and latest.created_at is not None
        and datetime.utcnow() - latest.created_at <= _DUPLICATE_WINDOW
    ):
        return RouteFeedbackRead.model_validate(latest)

    signal = UserSignal(
        user_id=subject,
        signal_type="route_feedback",
        entity_type="route",
        entity_id=payload.route_id,
        payload=signal_payload,
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return RouteFeedbackRead.model_validate(signal)
