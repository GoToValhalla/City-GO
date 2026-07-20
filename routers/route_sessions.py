"""Route session HTTP endpoints with X-Route-Session ownership."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_session import (
    RouteSessionCheckInRequest,
    RouteSessionCompleteResponse,
    RouteSessionRead,
    RouteSessionStartRequest,
    RouteSessionUpdateRequest,
)
from services.anonymous_ownership import ROUTE_SESSION_HEADER, require_ownership_header
from services.route_session_service import (
    RouteSessionConflict,
    RouteSessionNotFound,
    RouteSessionUnavailable,
    check_in_route_point,
    complete_route_session,
    get_route_session,
    start_route_session,
    update_route_session,
)

router = APIRouter(tags=["route-sessions"])


def _ownership_token(
    x_route_session: str | None = Header(default=None, alias=ROUTE_SESSION_HEADER),
) -> str:
    return require_ownership_header(x_route_session, header_name=ROUTE_SESSION_HEADER)


def _to_read(session, *, ownership_token: str | None = None) -> RouteSessionRead:
    body = RouteSessionRead.model_validate(session)
    if ownership_token is None:
        return body
    return body.model_copy(update={"ownership_token": ownership_token})


@router.post("/routes/{route_id}/sessions", response_model=RouteSessionRead)
def create_route_session(
    route_id: int,
    payload: RouteSessionStartRequest,
    db: Session = Depends(get_db),
) -> RouteSessionRead:
    try:
        session, raw = start_route_session(db, route_id=route_id, user_key=payload.user_key)
    except RouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RouteSessionUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _to_read(session, ownership_token=raw)


@router.get("/route-sessions/{session_id}", response_model=RouteSessionRead)
def read_route_session(
    session_id: int,
    ownership_token: str = Depends(_ownership_token),
    db: Session = Depends(get_db),
) -> RouteSessionRead:
    try:
        return _to_read(get_route_session(db, session_id, ownership_token=ownership_token))
    except RouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/route-sessions/{session_id}", response_model=RouteSessionRead)
def patch_route_session(
    session_id: int,
    payload: RouteSessionUpdateRequest,
    ownership_token: str = Depends(_ownership_token),
    db: Session = Depends(get_db),
) -> RouteSessionRead:
    try:
        return _to_read(
            update_route_session(
                db,
                session_id,
                ownership_token=ownership_token,
                status=payload.status,
                current_point_index=payload.current_point_index,
            )
        )
    except RouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RouteSessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/route-sessions/{session_id}/events/checkin", response_model=RouteSessionRead)
def check_in_route_session_point(
    session_id: int,
    payload: RouteSessionCheckInRequest,
    ownership_token: str = Depends(_ownership_token),
    db: Session = Depends(get_db),
) -> RouteSessionRead:
    try:
        return _to_read(
            check_in_route_point(
                db, session_id, payload.point_index, payload.action, ownership_token=ownership_token
            )
        )
    except RouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RouteSessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/route-sessions/{session_id}/complete", response_model=RouteSessionCompleteResponse)
def complete_route_session_endpoint(
    session_id: int,
    ownership_token: str = Depends(_ownership_token),
    db: Session = Depends(get_db),
) -> RouteSessionCompleteResponse:
    try:
        session = complete_route_session(db, session_id, ownership_token=ownership_token)
    except RouteSessionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RouteSessionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RouteSessionCompleteResponse(
        id=session.id,
        route_id=session.route_id,
        status="completed",
        visited_points=len(session.visited_point_indexes),
        skipped_points=len(session.skipped_point_indexes),
        total_points=len(session.points),
        completed_at=session.completed_at,
    )
