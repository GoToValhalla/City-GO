from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
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
from services.anonymous_ownership import ROUTE_SESSION_HEADER, require_ownership_header
from services.destination_route_resolution import resolve_route_build_request
from services.public_route_sanitizer import sanitize_user_route_state
from services.route_analytics_service import record_route_build
from services.route_builder_v2_service import RouteBuilderV2Error
from services.user_route_build_service import RouteBuildTimeoutError, UserRouteBuildService
from services.user_route_edit_service import UserRouteEditService
from services.user_route_session_service import (
    UserRouteSessionError,
    UserRouteSessionNotFound,
    UserRouteSessionService,
)
from services.user_route_state_integrity import UserRouteStateIntegrityError
from services.public_read_projection_service import PublicReadProjectionError
from services.projection_http_error import raise_projection_unavailable
from services.user_route_state_lifecycle_service import (
    RouteStateLifecycleService,
    UserRouteMutationRejectedError,
    UserRouteStateConflictError,
)

router = APIRouter(prefix="/user-routes", tags=["user-routes"])
_ROUTE_STATE_ERRORS = (UserRouteStateConflictError, UserRouteStateIntegrityError)
_lifecycle = RouteStateLifecycleService()


@router.post("/build", response_model=UserRouteState)
def build_user_route(payload: UserRouteBuildRequest, db: Session = Depends(get_db)) -> UserRouteState:
    if payload.start_source == "current_location" and (payload.lat is None or payload.lng is None):
        raise HTTPException(status_code=422, detail="lat/lng required for current_location")

    resolved_payload, block_reason = resolve_route_build_request(db, payload)
    if block_reason:
        raise HTTPException(status_code=422, detail={"partial_reason": block_reason})

    started = perf_counter()
    try:
        route = UserRouteBuildService().build(db=db, request=resolved_payload)
        issued = _lifecycle.issue_initial(db, route)
        db.commit()
    except RouteBuilderV2Error as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    except RouteBuildTimeoutError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": "route_build_deadline_exceeded", "message": str(exc)}) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc

    record_route_build(
        issued,
        source=f"user_route_build:{payload.build_mode}",
        latency_ms=_latency_ms(started),
        city_id=payload.city_id,
        user_id=payload.user_id,
    )
    return issued


@router.post("/preview", response_model=UserRouteState)
def preview_user_route(payload: UserRoutePreviewRequest, db: Session = Depends(get_db)) -> UserRouteState:
    try:
        route = UserRouteBuildService().build(db=db, request=UserRouteBuildRequest(**payload.model_dump()))
        issued = _lifecycle.issue_initial(
            db,
            route.model_copy(update={"status": "preview"}),
        )
        db.commit()
        return issued
    except RouteBuilderV2Error as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": "route_builder_v2_invalid_request", "message": str(exc)}) from exc
    except RouteBuildTimeoutError as exc:
        db.rollback()
        return _failed_preview(payload, exc)
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc
    except Exception as exc:
        db.rollback()
        print(f"user_route_preview_failed: {exc.__class__.__name__}: {exc}")
        return _failed_preview(payload, exc)


@router.post("/build-structured", response_model=UserRouteStructuredBuildResponse)
def build_structured_user_route(
    payload: UserRouteStructuredBuildRequest,
    db: Session = Depends(get_db),
) -> UserRouteStructuredBuildResponse:
    try:
        return UserRouteEditService().structured_options(db, payload)
    except PublicReadProjectionError as exc:
        raise_projection_unavailable(exc, read_path="routing")


@router.post("/correct", response_model=UserRouteState)
def correct_user_route(payload: UserRouteCorrectRequest, db: Session = Depends(get_db)) -> UserRouteState:
    started = perf_counter()
    try:
        issued = _lifecycle.correct(db, payload)
        db.commit()
    except UserRouteMutationRejectedError as exc:
        db.rollback()
        raise _route_mutation_http_error(exc) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc
    except Exception:
        db.rollback()
        raise

    record_route_build(
        issued,
        source=f"user_route_correct:{payload.action}",
        latency_ms=_latency_ms(started),
        city_id=issued.context.city_id,
        user_id=issued.context.user_id,
    )
    return issued


@router.post("/{route_id}/update", response_model=UserRouteState)
def update_user_route(
    route_id: str,
    payload: UserRouteUpdateRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_route_id_matches(route_id, payload.current_route)
    try:
        issued = _lifecycle.update_order(db, payload)
        db.commit()
        return issued
    except UserRouteMutationRejectedError as exc:
        db.rollback()
        raise _route_mutation_http_error(exc) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{route_id}/replace-place", response_model=UserRouteState)
def replace_user_route_place(
    route_id: str,
    payload: UserRouteReplacePlaceRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_route_id_matches(route_id, payload.current_route)
    try:
        issued = _lifecycle.replace_place(db, payload)
        db.commit()
        return issued
    except UserRouteMutationRejectedError as exc:
        db.rollback()
        raise _route_mutation_http_error(exc) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.get("/{route_id}/alternatives/{place_id}")
def read_user_route_alternatives_deprecated(route_id: str, place_id: str) -> None:
    del route_id, place_id
    raise HTTPException(
        status_code=410,
        detail={
            "code": "USE_POST_ALTERNATIVES",
            "message": "GET alternatives is removed. Use POST /{route_id}/alternatives/{place_id}.",
        },
    )


@router.post("/{route_id}/alternatives/{place_id}", response_model=UserRouteAlternativesResponse)
def read_user_route_alternatives_from_state(
    route_id: str,
    place_id: str,
    payload: UserRouteState,
    db: Session = Depends(get_db),
) -> UserRouteAlternativesResponse:
    _ensure_route_id_matches(route_id, payload)
    try:
        result = _lifecycle.read_alternatives(db, payload, place_id)
        db.commit()
        return result
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc


@router.post("/{route_id}/add-place", response_model=UserRouteState)
def add_user_route_place(
    route_id: str,
    payload: UserRouteAddPlaceRequest,
    db: Session = Depends(get_db),
) -> UserRouteState:
    _ensure_route_id_matches(route_id, payload.current_route)
    try:
        issued = _lifecycle.add_place(db, payload)
        db.commit()
        return issued
    except UserRouteMutationRejectedError as exc:
        db.rollback()
        raise _route_mutation_http_error(exc) from exc
    except PublicReadProjectionError as exc:
        db.rollback()
        raise_projection_unavailable(exc, read_path="routing")
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{route_id}/session/start", response_model=UserRouteSessionState)
def start_user_route_session(
    route_id: str,
    payload: UserRouteSessionStartRequest,
    x_route_session: str | None = Header(default=None, alias=ROUTE_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> UserRouteSessionState:
    _ensure_route_id_matches(route_id, payload.current_route)
    try:
        result = _lifecycle.start_session(db, payload, ownership_token=x_route_session)
        db.commit()
        return result
    except UserRouteSessionNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except UserRouteSessionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": "route_session_invalid_request", "message": str(exc)}) from exc
    except _ROUTE_STATE_ERRORS as exc:
        db.rollback()
        raise _route_state_http_error(exc) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc


@router.post("/sessions/{session_id}/action", response_model=UserRouteSessionState)
def update_user_route_session(
    session_id: int,
    payload: UserRouteSessionActionRequest,
    x_route_session: str | None = Header(default=None, alias=ROUTE_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> UserRouteSessionState:
    token = require_ownership_header(x_route_session, header_name=ROUTE_SESSION_HEADER)
    try:
        result = UserRouteSessionService().apply_action(db, session_id, payload, ownership_token=token)
        db.commit()
        return result
    except UserRouteSessionNotFound as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except UserRouteSessionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail={"code": "route_session_invalid_transition", "message": str(exc)}) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise _database_http_error(exc) from exc


@router.get("/sessions/{session_id}", response_model=UserRouteSessionState)
def read_user_route_session(
    session_id: int,
    route_id: str = Query(...),
    x_route_session: str | None = Header(default=None, alias=ROUTE_SESSION_HEADER),
    db: Session = Depends(get_db),
) -> UserRouteSessionState:
    """Read-only restore check: proves ownership AND that this session
    belongs to `route_id`, without mutating anything. Used by clients
    restoring a persisted session on reopen, before showing it as active
    progress for the currently displayed route."""
    token = require_ownership_header(x_route_session, header_name=ROUTE_SESSION_HEADER)
    try:
        return UserRouteSessionService().validate(db, session_id, route_id=route_id, ownership_token=token)
    except UserRouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": str(exc)}) from exc
    except SQLAlchemyError as exc:
        raise _database_http_error(exc) from exc


def _failed_preview(payload: UserRoutePreviewRequest, exc: BaseException) -> UserRouteState:
    is_timeout = isinstance(exc, RouteBuildTimeoutError)
    return sanitize_user_route_state(
        UserRouteState(
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
        )
    )


def _ensure_route_id_matches(route_id: str, current_route: UserRouteState) -> None:
    if str(current_route.route_id) == str(route_id):
        return
    raise HTTPException(
        status_code=409,
        detail={
            "code": "route_state_conflict",
            "message": "Route mutation payload does not match the route id in the URL.",
            "route_id": str(route_id),
            "payload_route_id": str(current_route.route_id),
            "payload_revision": int(current_route.revision),
        },
    )


def _route_mutation_http_error(exc: BaseException) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "route_mutation_rejected",
            "message": str(exc),
        },
    )


def _route_state_http_error(exc: BaseException) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail={
            "code": "route_state_conflict",
            "message": "Route state is missing, stale, modified, or already superseded.",
        },
    )


def _database_http_error(exc: BaseException) -> HTTPException:
    return HTTPException(
        status_code=503,
        detail={
            "code": "route_state_database_unavailable",
            "message": "Route state storage is temporarily unavailable.",
        },
    )


def _latency_ms(started: float) -> int:
    return int((perf_counter() - started) * 1000)
