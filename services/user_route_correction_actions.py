from __future__ import annotations

from sqlalchemy.orm import Session

from schemas.user_route import UserRouteCorrectRequest
from services.user_route_correction_policy import (
    correction_excluded_ids,
    same_category,
    shorten_target_place_id,
)
from services.user_route_place_loader import load_place
from services.user_route_replacement_loader import find_replacement_place


def corrected_places(db: Session, request: UserRouteCorrectRequest, places: list) -> list:
    if request.action == "shorten_route":
        return _without_place(places, shorten_target_place_id(request.current_route))
    if request.action == "extend_route":
        return _with_replacement(db, request, places, None)
    if request.action == "remove_place":
        remaining = _without_place(places, request.target_place_id)
        target = load_place(db, request.target_place_id)
        return _with_replacement(db, request, remaining, same_category(target))
    return places


def _without_place(places: list, place_id: str | None) -> list:
    return [place for place in places if str(place.id) != str(place_id)]


def _with_replacement(
    db: Session,
    request: UserRouteCorrectRequest,
    places: list,
    category: str | None,
) -> list:
    replacement = find_replacement_place(
        db,
        route=request.current_route,
        category=category,
        excluded_ids=correction_excluded_ids(request.current_route, request.target_place_id),
    )
    return [*places, replacement] if replacement is not None else places
