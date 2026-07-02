from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteAlternativesResponse,
    UserRouteBuildRequest,
    UserRouteCorrectRequest,
    UserRoutePreviewRequest,
    UserRouteReplacePlaceRequest,
    UserRouteState,
    UserRouteStructuredBuildRequest,
    UserRouteStructuredBuildResponse,
    UserRouteUpdateRequest,
)
from services.route_analytics_service import record_route_build
from services.route_builder_v2_service import RouteBuilderV2Error
from services.user_route_build_service import UserRouteBuildService
from services.user_route_correct_service import UserRouteCorrectService
from services.user_route_edit_service import UserRouteEditService

router = APIRouter(prefix="/user-routes", tags=["user-routes"])


@router.post("/build", response_model=UserRouteState)
def build_user_route(
    payload: UserRouteBuildRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    if payload.start_source == "current_location" and (payload.lat is None or payload.lng is None):
        raise HTTPException(status_code=422, detail="lat/lng required for current_location")

    started = perf_counter()
    try:
        route = UserRouteBuildService().build(db=db, request=payload)
    except RouteBuilderV2Error as exc:
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    record_route_build(
        db,
        route,
        source=f"user_route_build:{payload.build_mode}",
        latency_ms=_latency_ms(started),
        city_id=payload.city_id,
        user_id=payload.user_id,
    )
    return route


@router.post("/preview", response_model=UserRouteState)
def preview_user_route(
    payload: UserRoutePreviewRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    try:
        route = UserRouteBuildService().build(db=db, request=UserRouteBuildRequest(**payload.model_dump()))
        return route.model_copy(update={"status": "preview"})
    except RouteBuilderV2Error as exc:
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    except Exception as exc:
        return UserRouteState(
            route_id="preview-unavailable",
            status="preview_failed",
            partial_reason="route_preview_mapping_failed",
            context=payload,
            total_places=0,
            total_minutes=0,
            total_estimated_minutes=0,
            estimated_distance=0.0,
            has_warnings=True,
            warning_count=1,
            quality_score=0.0,
            quality_status="failed",
            warnings=["route_preview_mapping_failed"],
            debug_trace=[
                {
                    "stage": "preview_response_mapping",
                    "status": "failed",
                    "error": exc.__class__.__name__,
                    "message": str(exc),
                }
            ],
        )


@router.post("/build-structured", response_model=UserRouteStructuredBuildResponse)
def build_structured_user_route(
    payload: UserRouteStructuredBuildRequest,
    db: Session = Depends(get_db),
) -> UserRouteStructuredBuildResponse:
    return UserRouteEditService().structured_options(db, payload)


@router.post("/correct", response_model=UserRouteState)
def correct_user_route(
    payload: UserRouteCorrectRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    started = perf_counter()
    route = UserRouteCorrectService().correct(db=db, request=payload)
    record_route_build(
        db,
        route,
        source=f"user_route_correct:{payload.action}",
        latency_ms=_latency_ms(started),
        city_id=route.context.city_id,
        user_id=route.context.user_id,
    )
    return route


@router.post("/{route_id}/update", response_model=UserRouteState)
def update_user_route(
    route_id: str,
    payload: UserRouteUpdateRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_current_route_matches(route_id, payload.current_route)
    route = UserRouteEditService().update_order(db, payload)
    return route.model_copy(update={"route_id": route_id})


@router.post("/{route_id}/replace-place", response_model=UserRouteState)
def replace_user_route_place(
    route_id: str,
    payload: UserRouteReplacePlaceRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_current_route_matches(route_id, payload.current_route)
    route = UserRouteEditService().replace_place(db, payload)
    return route.model_copy(update={"route_id": route_id})


@router.get("/{route_id}/alternatives/{place_id}", response_model=UserRouteAlternativesResponse)
def read_user_route_alternatives(
    route_id: str,
    place_id: str,
    current_route: str = Query(default=""),
    db: Session = Depends(get_db),
) -> UserRouteAlternativesResponse:
    # GET endpoint keeps the public contract path, but current route state is not persisted yet.
    # Until Active Route Session is implemented, return an empty deterministic response.
    return UserRouteAlternativesResponse(route_id=route_id, place_id=place_id, options=[])


@router.post("/{route_id}/alternatives/{place_id}", response_model=UserRouteAlternativesResponse)
def read_user_route_alternatives_from_state(
    route_id: str,
    place_id: str,
    payload: UserRouteState,
    db: Session = Depends(get_db),
) -> UserRouteAlternativesResponse:
    _ensure_current_route_matches(route_id, payload)
    return UserRouteEditService().alternatives(db, payload.model_copy(update={"route_id": route_id}), place_id)


@router.post("/{route_id}/add-place", response_model=UserRouteState)
def add_user_route_place(
    route_id: str,
    payload: UserRouteAddPlaceRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_current_route_matches(route_id, payload.current_route)
    route = UserRouteEditService().add_place(db, payload)
    return route.model_copy(update={"route_id": route_id})


def _ensure_current_route_matches(route_id: str, current_route: UserRouteState) -> None:
    payload_route_id = str(current_route.route_id)
    if payload_route_id == str(route_id):
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "route_state_conflict",
            "message": "Route mutation payload does not match the route id in the URL.",
            "route_id": str(route_id),
            "payload_route_id": payload_route_id,
            "payload_revision": int(current_route.revision),
        },
    )


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
