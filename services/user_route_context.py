from __future__ import annotations

from schemas.user_route import UserRouteIntent
from services.context_merge_service import RequestContext


from services.destination_route_resolution import intent_to_request_context_fields


def to_request_context(intent: UserRouteIntent) -> RequestContext:
    return RequestContext(
        location=(intent.lat, intent.lng),
        city_id=intent.city_id,
        time_budget_minutes=intent.time_budget_minutes,
        time_of_day=intent.time_of_day,
        route_time_mode=intent.route_time_mode,
        interests=intent.interests,
        avoided_categories=intent.avoided_categories,
        excluded_place_ids=intent.excluded_place_ids,
        budget_level=intent.budget_level,
        pace_mode=intent.pace_mode,
        is_visiting=intent.is_visiting,
        visit_city_id=intent.visit_city_id,
        visit_days=intent.visit_days,
        **intent_to_request_context_fields(intent),
    )


def merge_unique(left: list[str], right: list[str]) -> list[str]:
    return list(dict.fromkeys([*left, *right]))


def with_updates(
    intent: UserRouteIntent,
    *,
    lat: float | None = None,
    lng: float | None = None,
    time_budget_minutes: int | None = None,
    avoided_categories: list[str] | None = None,
    excluded_place_ids: list[str] | None = None,
) -> UserRouteIntent:
    return intent.model_copy(
        update={
            "lat": intent.lat if lat is None else lat,
            "lng": intent.lng if lng is None else lng,
            "time_budget_minutes": time_budget_minutes or intent.time_budget_minutes,
            "avoided_categories": avoided_categories or intent.avoided_categories,
            "excluded_place_ids": excluded_place_ids or intent.excluded_place_ids,
        }
    )
