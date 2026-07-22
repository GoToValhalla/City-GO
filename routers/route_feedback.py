from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_feedback import RouteFeedbackCreate, RouteFeedbackRead
from services.anonymous_ownership import optional_anonymous_session
from services.route_feedback_application import dedup_key as _dedup_key
from services.route_feedback_application import dedup_subject as _dedup_subject
from services.route_feedback_application import submit_route_feedback

router = APIRouter(prefix="/route-feedback", tags=["route-feedback"])

@router.post("/", response_model=RouteFeedbackRead)
def post_route_feedback(
    payload: RouteFeedbackCreate,
    anonymous_subject: str | None = Depends(optional_anonymous_session),
    db: Session = Depends(get_db),
) -> RouteFeedbackRead:
    return submit_route_feedback(db, payload, anonymous_subject=anonymous_subject)
