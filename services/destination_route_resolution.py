"""Resolve destination/city for user route build (compatibility v1)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from schemas.user_route import UserRouteBuildRequest, UserRouteIntent
from services.city_destination_compatibility import (
    get_destination_by_slug,
    resolve_destination_to_city_slug,
)
from services.destination_route_guard import validate_trip_type_for_destination


def resolve_route_build_request(
    db: Session,
    request: UserRouteBuildRequest,
) -> tuple[UserRouteBuildRequest, str | None]:
    """Returns (resolved_request, blocking_partial_reason)."""
    dest_slug = request.destination_slug
    dest_id = request.destination_id
    if dest_slug is None and dest_id is not None:
        from services.city_destination_compatibility import get_destination_by_id

        row = get_destination_by_id(db, int(dest_id))
        dest_slug = row.slug if row else None

    if dest_slug is None and request.city_id:
        return request, None

    if dest_slug is None:
        return request, None

    dest = get_destination_by_slug(db, dest_slug)
    if dest is None:
        return request, None

    guard = validate_trip_type_for_destination(
        db,
        destination_slug=dest.slug,
        destination_id=dest.id,
        trip_type=request.trip_type or "walking",
    )
    if guard:
        return request, guard

    legacy_city_slug = resolve_destination_to_city_slug(db, dest)
    updates: dict[str, object] = {
        "destination_slug": dest.slug,
        "destination_id": str(dest.id),
    }
    if legacy_city_slug and not request.city_id:
        updates["city_id"] = legacy_city_slug
    return request.model_copy(update=updates), None


def intent_to_request_context_fields(intent: UserRouteIntent) -> dict[str, object]:
    return {
        "destination_id": intent.destination_id,
        "destination_slug": intent.destination_slug,
        "trip_type": intent.trip_type or "walking",
    }
