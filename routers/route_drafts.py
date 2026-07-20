from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_draft import (
    AddPointRequest,
    PlaceSearchResponse,
    RandomRouteRequest,
    RemovePointRequest,
    ReplacePointRequest,
    RouteDraftRead,
)
from services.route_draft_access import SESSION_HEADER
from services.route_draft_errors import RouteDraftError
from services.route_draft_loader import get_public_draft_or_error
from services.route_draft_mutations import add_point, remove_point, replace_point
from services.route_draft_search import search_places
from services.route_draft_serializer import serialize_draft, serialize_public_draft_view
from services.route_random_service import create_random_route_draft

router = APIRouter(prefix="/routes", tags=["route-drafts"])


def _draft_error(exc: RouteDraftError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": exc.message})


def _session_token(
    x_route_draft_session: str = Header(
        ...,
        alias=SESSION_HEADER,
        min_length=8,
        max_length=255,
    ),
) -> str:
    return x_route_draft_session


@router.post("/random", response_model=RouteDraftRead)
def create_random_route(payload: RandomRouteRequest, db: Session = Depends(get_db)) -> RouteDraftRead:
    draft = create_random_route_draft(db, payload)
    if draft is None:
        raise HTTPException(status_code=404, detail={"code": "CITY_NOT_FOUND", "message": "City not found"})
    return serialize_draft(draft)


@router.get("/drafts/{draft_id}", response_model=RouteDraftRead)
def read_route_draft(
    draft_id: int,
    session_token: str = Depends(_session_token),
    db: Session = Depends(get_db),
) -> RouteDraftRead:
    try:
        draft = get_public_draft_or_error(db, draft_id, session_token=session_token)
        return serialize_public_draft_view(db, draft)
    except RouteDraftError as exc:
        raise _draft_error(exc) from exc


@router.post("/drafts/{draft_id}/remove-point", response_model=RouteDraftRead)
def remove_route_draft_point(
    draft_id: int,
    payload: RemovePointRequest,
    session_token: str = Depends(_session_token),
    db: Session = Depends(get_db),
) -> RouteDraftRead:
    try:
        draft = get_public_draft_or_error(db, draft_id, session_token=session_token, for_update=True)
        return serialize_draft(remove_point(db, draft, payload.point_id, payload.version))
    except RouteDraftError as exc:
        raise _draft_error(exc) from exc


@router.post("/drafts/{draft_id}/add-point", response_model=RouteDraftRead)
def add_route_draft_point(
    draft_id: int,
    payload: AddPointRequest,
    session_token: str = Depends(_session_token),
    db: Session = Depends(get_db),
) -> RouteDraftRead:
    try:
        draft = get_public_draft_or_error(db, draft_id, session_token=session_token, for_update=True)
        updated = add_point(
            db, draft, payload.place_id, payload.after_position, payload.version, payload.allow_readd
        )
        return serialize_draft(updated)
    except RouteDraftError as exc:
        raise _draft_error(exc) from exc


@router.post("/drafts/{draft_id}/replace-point", response_model=RouteDraftRead)
def replace_route_draft_point(
    draft_id: int,
    payload: ReplacePointRequest,
    session_token: str = Depends(_session_token),
    db: Session = Depends(get_db),
) -> RouteDraftRead:
    try:
        draft = get_public_draft_or_error(db, draft_id, session_token=session_token, for_update=True)
        updated = replace_point(
            db, draft, payload.point_id, payload.replacement_place_id, payload.version
        )
        return serialize_draft(updated)
    except RouteDraftError as exc:
        raise _draft_error(exc) from exc


@router.get("/drafts/{draft_id}/search-places", response_model=PlaceSearchResponse)
def search_route_draft_places(
    draft_id: int,
    session_token: str = Depends(_session_token),
    q: str | None = Query(default=None),
    action: str = Query(default="add"),
    point_id: int | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
) -> PlaceSearchResponse:
    try:
        draft = get_public_draft_or_error(db, draft_id, session_token=session_token)
        items = search_places(db, draft, query=q, action=action, point_id=point_id, limit=limit)
        return PlaceSearchResponse(items=items)
    except RouteDraftError as exc:
        raise _draft_error(exc) from exc
