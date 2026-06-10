from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from models.user_signal import UserSignal
from schemas.route_feedback import RouteFeedbackCreate, RouteFeedbackRead

router = APIRouter(prefix="/route-feedback", tags=["route-feedback"])


@router.post("/", response_model=RouteFeedbackRead)
def post_route_feedback(payload: RouteFeedbackCreate, db: Session = Depends(get_db)) -> RouteFeedbackRead:
    """Сохраняет оценку маршрута как user signal для будущего обучения рекомендаций."""
    signal = UserSignal(
        user_id=payload.user_id or "anonymous",
        signal_type="route_feedback",
        entity_type="route",
        entity_id=payload.route_id,
        payload={
            "rating": payload.rating,
            "comment": payload.comment,
            "source": payload.source,
            "liked_place_ids": payload.liked_place_ids,
            "disliked_place_ids": payload.disliked_place_ids,
            "skipped_place_ids": payload.skipped_place_ids,
            "problem_types": payload.problem_types,
        },
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return RouteFeedbackRead.model_validate(signal)
