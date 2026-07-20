from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.route_draft import RouteDraft, RouteDraftPoint
from services.route_draft_access import get_accessible_draft_or_error
from services.route_draft_errors import RouteDraftError
from services.route_draft_rules import eligible_place_query


def get_draft_or_error(db: Session, draft_id: int) -> RouteDraft:
    """Internal existence lookup only — not for public HTTP handlers."""
    draft = db.query(RouteDraft).filter(RouteDraft.id == draft_id).first()
    if draft is None:
        raise RouteDraftError("DRAFT_NOT_FOUND", "Draft not found", 404)
    return draft


def get_public_draft_or_error(
    db: Session,
    draft_id: int,
    *,
    session_token: str | None,
    for_update: bool = False,
) -> RouteDraft:
    """Canonical public loader: ownership + lifecycle only (no writes)."""
    return get_accessible_draft_or_error(
        db, draft_id, session_token=session_token, for_update=for_update
    )


def check_version(draft: RouteDraft, version: int) -> None:
    if draft.version != version:
        raise RouteDraftError("STALE_DRAFT_VERSION", "Draft version is stale", 409)


def point_or_error(draft: RouteDraft, point_id: int) -> RouteDraftPoint:
    point = next((item for item in draft.points if item.id == point_id), None)
    if point is None:
        raise RouteDraftError("POINT_NOT_FOUND", "Point not found", 404)
    return point


def eligible_place_or_error(db: Session, city_id: int, place_id: int) -> Place:
    place = eligible_place_query(db.query(Place), city_id).filter(Place.id == place_id).first()
    if place is None:
        raise RouteDraftError("PLACE_NOT_ELIGIBLE", "Place is not eligible for this draft", 400)
    return place


def route_place_ids(draft: RouteDraft) -> set[int]:
    return {int(item.place_id) for item in draft.points}
