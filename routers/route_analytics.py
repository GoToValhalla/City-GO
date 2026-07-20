from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_analytics import RouteAnalyticsSummary, UserRouteHistoryItem
from services.anonymous_ownership import require_anonymous_session
from services.route_analytics_service import route_analytics_summary
from services.user_route_history_service import user_route_history

router = APIRouter(prefix="/route-analytics", tags=["route-analytics"])

_NOT_FOUND = {"code": "NOT_FOUND", "message": "Resource not found"}


@router.get("/summary", response_model=RouteAnalyticsSummary)
def get_route_analytics_summary(db: Session = Depends(get_db)) -> RouteAnalyticsSummary:
    return RouteAnalyticsSummary.model_validate(route_analytics_summary(db))


@router.get("/users/me/history", response_model=list[UserRouteHistoryItem])
def get_my_route_history(
    subject: str = Depends(require_anonymous_session),
    db: Session = Depends(get_db),
) -> list[UserRouteHistoryItem]:
    return list(map(UserRouteHistoryItem.model_validate, user_route_history(db, subject)))


@router.get("/users/{user_id}/history")
def legacy_user_route_history(user_id: str) -> None:
    del user_id
    raise HTTPException(status_code=404, detail=_NOT_FOUND)
