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
    UserRouteSessionActionRequest,
    UserRouteSessionStartRequest,
    UserRouteSessionState,
    UserRouteState,
    UserRouteStructuredBuildRequest,
    UserRouteStructuredBuildResponse,
    UserRouteUpdateRequest,
)
from services.public_route_sanitizer import sanitize_user_route_state
from services.route_analytics_service import record_route_build
from services.route_builder_v2_service import RouteBuilderV2Error
from services.destination_route_resolution import resolve_route_build_request
from services.user_route_build_service import RouteBuildTimeoutError, UserRouteBuildService
from services.user_route_correct_service import UserRouteCorrectService
from services.user_route_edit_service import UserRouteEditService
from services.user_route_session_service import UserRouteSessionError, UserRouteSessionService

router = APIRouter(prefix="/user-routes", tags=["user-routes"])


@router.post("/build", response_model=UserRouteState)
def build_user_route(
    payload: UserRouteBuildRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    if payload.start_source == "current_location" and (payload.lat is None or payload.lng is None):
        raise HTTPException(status_code=422, detail="lat/lng required for current_location")

    resolved_payload, block_reason = resolve_route_build_request(db, payload)
    if block_reason:
        raise HTTPException(status_code=422, detail={"partial_reason": block_reason})

    started = perf_counter()
    try:
        route = UserRouteBuildService().build(db=db, request=resolved_payload)
    except RouteBuilderV2Error as exc:
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    except RouteBuildTimeoutError as exc:
        raise HTTPException(status_code=422, detail={"code": "route_build_deadline_exceeded", "message": str(exc)}) from exc
    record_route_build(
        db,
        route,
        source=f"user_route_build:{payload.build_mode}",
        latency_ms=_latency_ms(started),
        city_id=payload.city_id,
        user_id=payload.user_id,
    )
    return sanitize_user_route_state(route)


@router.post("/preview", response_model=UserRouteState)
def preview_user_route(
    payload: UserRoutePreviewRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    try:
        route = UserRouteBuildService().build(db=db, request=UserRouteBuildRequest(**payload.model_dump()))
        return sanitize_user_route_state(route.model_copy(update={"status": "preview"}))
    except RouteBuilderV2Error as exc:
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    except Exception as exc:
        print(f"user_route_preview_failed: {exc.__class__.__name__}: {exc}")
        is_timeout = isinstance(exc, RouteBuildTimeoutError)
        return sanitize_user_route_state(UserRouteState(
            route_id="preview-unavailable",
            status="preview_failed",
            partial_reason="route_preview_deadline_exceeded" if is_timeout else "route_preview_mapping_failed",
            context=payload,
            total_places=0,
            total_minutes=0,
            total_estimated_minutes=0,
            estimated_distance=0.0,
            has_warnings=True,
            warning_count=1,
            quality_score=0.0,
            quality_status="failed",
            warnings=["Маршрут не удалось предварительно собрать."],
            user_warnings=[
                {
                    "type": "route",
                    "severity": "warning",
                    "user_message": "Маршрут не удалось предварительно собрать.",
                    "affected_place_ids": [],
                    "action_hint": "Попробуйте изменить время, интересы или стартовую точку.",
                }
            ],
            debug_trace=[
                {
                    "stage": "preview_response_mapping",
                    "status": "failed",
                    "error": exc.__class__.__name__,
                    "message": "Preview route build exceeded internal deadline." if is_timeout else "Preview route build failed.",
                }
            ],
        ))


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
    return sanitize_user_route_state(route)


@router.post("/{route_id}/update", response_model=UserRouteState)
def update_user_route(
    route_id: str,
    payload: UserRouteUpdateRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_current_route_matches(route_id, payload.current_route)
    route = UserRouteEditService().update_order(db, payload)
    return sanitize_user_route_state(route.model_copy(update={"route_id": route_id}))


@router.post("/{route_id}/replace-place", response_model=UserRouteState)
def replace_user_route_place(
    route_id: str,
    payload: UserRouteReplacePlaceRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_current_route_matches(route_id, payload.current_route)
    route = UserRouteEditService().replace_place(db, payload)
    return sanitize_user_route_state(route.model_copy(update={"route_id": route_id}))


@router.get("/{route_id}/alternatives/{place_id}", response_model=UserRouteAlternativesResponse)
def read_user_route_alternatives(
    route_id: str,
    place_id: str,
    current_route: str = Query(default=""),
    db: Session = Depends(get_db),
) -> UserRouteAlternativesResponse:
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
    return sanitize_user_route_state(route.model_copy(update={"route_id": route_id}))


@router.post("/{route_id}/session/start", response_model=UserRouteSessionState)
def start_user_route_session(
    route_id: str,
    payload: UserRouteSessionStartRequest,
    db: Session = Depends(get_db),
) -> UserRouteSessionState:
    _ensure_current_route_matches(route_id, payload.current_route)
    try:
        return UserRouteSessionService().start(db, payload)
    except UserRouteSessionError as exc:
        raise HTTPException(status_code=422, detail={"code": "route_session_invalid_request", "message": str(exc)}) from exc


@router.post("/sessions/{session_id}/action", response_model=UserRouteSessionState)
def update_user_route_session(
    session_id: int,
    payload: UserRouteSessionActionRequest,
    db: Session = Depends(get_db),
) -> UserRouteSessionState:
    try:
        return UserRouteSessionService().apply_action(db, session_id, payload)
    except UserRouteSessionError as exc:
        raise HTTPException(status_code=422, detail={"code": "route_session_invalid_transition", "message": str(exc)}) from exc


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
