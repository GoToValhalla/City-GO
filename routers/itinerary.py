"""LEGACY ROUTER for old itinerary endpoints.

Status: registered for backward compatibility, but `/routes/generate` is already
deprecated and points clients to `POST /v1/user-routes/build`.

Active source of truth for new route generation:
- `routers.user_routes`
- `services.route_builder_flow`
- user route build/draft/session services.

Rules:
- Do not add new route features here.
- Keep old endpoints only for compatibility until consumers migrate.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.itinerary import ItineraryGenerateRequest, ItineraryGenerateResponse
from schemas.itinerary_replan import ItineraryReplanRequest, ItineraryReplanResponse
from services.itinerary_replan_service import replan_itinerary
from services.itinerary_service import generate_itinerary_stub
from services.route_generation_logging import (
    log_route_generation_failed,
    log_route_generation_started,
    log_route_generation_success,
)
from services.route_toggle_guard import assert_route_generation_allowed

router = APIRouter(prefix="/routes", tags=["itinerary"])


@router.post("/generate", response_model=ItineraryGenerateResponse, deprecated=True)
def generate_itinerary(
    request: ItineraryGenerateRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> ItineraryGenerateResponse:
    response.headers["X-Deprecated"] = "Use POST /v1/user-routes/build instead"
    assert_route_generation_allowed(db, city_slug=request.city_slug)
    log_route_generation_started(db, source="itinerary_generate", city_slug=request.city_slug)
    response_body = generate_itinerary_stub(db=db, request=request)
    stops = len(response_body.points or [])
    if stops > 0:
        log_route_generation_success(db, source="itinerary_generate", city_slug=request.city_slug, stops=stops)
    else:
        log_route_generation_failed(
            db, source="itinerary_generate", city_slug=request.city_slug, reason="no_selected_places",
        )
    return response_body


@router.post("/replan", response_model=ItineraryReplanResponse)
def replan_route(
    request: ItineraryReplanRequest,
    db: Session = Depends(get_db),
) -> ItineraryReplanResponse:
    city_slug = request.current_route.city_slug
    assert_route_generation_allowed(db, city_slug=city_slug)
    log_route_generation_started(db, source="itinerary_replan", city_slug=city_slug)
    response = replan_itinerary(db=db, request=request)
    stops = len(response.points or [])
    if stops > 0:
        log_route_generation_success(db, source="itinerary_replan", city_slug=city_slug, stops=stops)
    else:
        log_route_generation_failed(
            db, source="itinerary_replan", city_slug=city_slug, reason="no_selected_places",
        )
    return response
