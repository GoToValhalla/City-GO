from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.external_navigation import ExternalNavigationEventRequest, ExternalNavigationEventResponse
from services.external_navigation_service import record_external_navigation_event

router = APIRouter(prefix="/navigation-events", tags=["navigation-events"])


@router.post("/", response_model=ExternalNavigationEventResponse)
def create_navigation_event(
    route_id: str,
    payload: ExternalNavigationEventRequest,
    session_id: int | None = None,
    db: Session = Depends(get_db),
) -> ExternalNavigationEventResponse:
    recorded = record_external_navigation_event(db, route_id=route_id, session_id=session_id, payload=payload)
    return ExternalNavigationEventResponse(recorded=recorded)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
