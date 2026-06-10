from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_analytics import RouteAnalyticsSummary, UserRouteHistoryItem
from services.route_analytics_service import route_analytics_summary
from services.user_route_history_service import user_route_history

router = APIRouter(prefix="/route-analytics", tags=["route-analytics"])


@router.get("/summary", response_model=RouteAnalyticsSummary)
def get_route_analytics_summary(db: Session = Depends(get_db)) -> RouteAnalyticsSummary:
    return RouteAnalyticsSummary.model_validate(route_analytics_summary(db))


@router.get("/users/{user_id}/history", response_model=list[UserRouteHistoryItem])
def get_user_route_history(user_id: str, db: Session = Depends(get_db)) -> list[UserRouteHistoryItem]:
    return list(map(UserRouteHistoryItem.model_validate, user_route_history(db, user_id)))
