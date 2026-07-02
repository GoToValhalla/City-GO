"""LEGACY ITINERARY ORCHESTRATION STACK.

Status: kept for backward compatibility with old `/routes/generate` and
`/routes/replan` endpoints.

Active source of truth for new route generation:
- `services.route_builder_flow`
- `services.user_route_build_service`
- route draft/session services.

Rules:
- Do not add new route product features here.
- Do not use this stack for new Telegram/Web route flows.
- Keep only until old itinerary clients are migrated.
"""

from sqlalchemy.orm import Session

from models.city import City
from schemas.itinerary import (
    CurrentRouteContextRead,
    CurrentRoutePointRead,
    ItineraryGenerateRequest,
    ItineraryGenerateResponse,
    ItineraryPointRead,
    StartContextRead,
)
from services.itinerary_candidate_service import get_candidate_places
from services.itinerary_explanation_service import (
    build_place_reason,
    build_route_explanation,
)
from services.itinerary_route_builder_service import build_route_from_ranked_places
from services.itinerary_scoring_service import rank_candidate_places
from services.itinerary_text_parser import (
    merge_explicit_fields_and_text_constraints,
    parse_route_intent,
)
from services.itinerary_time_service import (
    estimate_route_opening_statuses,
    resolve_timezone_name,
)
from services.start_context_resolver import resolve_start_context


def get_city_by_slug(db: Session, city_slug: str) -> City | None:
    return db.query(City).filter(City.slug == city_slug).first()


def build_start_context_read(
    request: ItineraryGenerateRequest,
    db: Session,
) -> StartContextRead:
    start_context_input = request.start_context
    geo = start_context_input.geo if start_context_input and start_context_input.geo else None

    resolved = resolve_start_context(
        place_id=start_context_input.place_id if start_context_input else None,
        geo_lat=geo.lat if geo else None,
        geo_lng=geo.lng if geo else None,
        geo_acc_m=geo.accuracy_m if geo else None,
        address=start_context_input.address if start_context_input else None,
        city_slug=(
            start_context_input.city
            if start_context_input and start_context_input.city
            else request.city_slug
        ),
        city_name=None,
        legacy_lat=start_context_input.lat if start_context_input else None,
        legacy_lng=start_context_input.lng if start_context_input else None,
        db=db,
    )

    return StartContextRead(
        source=resolved.source.value,
        accuracy_tier=resolved.accuracy_tier.value,
        lat=resolved.lat,
        lng=resolved.lng,
        display_label=resolved.display_label,
        raw_address=resolved.raw_address,
        warning_message=resolved.warning_message,
    )


def build_itinerary_summary(
    request: ItineraryGenerateRequest,
    merged_context: dict,
) -> str:
    summary_parts: list[str] = []

    summary_parts.append(f"Draft itinerary for {request.city_slug}")

    if request.query:
        summary_parts.append(f"based on query: {request.query}")

    if merged_context.get("route_mode"):
        summary_parts.append(f"mode: {merged_context['route_mode']}")

    if merged_context.get("time_mode") == "explicit_budget":
        if merged_context.get("time_budget_minutes") is not None:
            summary_parts.append(
                f"time budget: {merged_context['time_budget_minutes']} minutes"
            )

    if merged_context.get("preferences", {}).get("anti_tourist"):
        summary_parts.append("anti-tourist preference")

    interests = merged_context.get("preferences", {}).get("interests", [])
    if interests:
        summary_parts.append(f"interests: {', '.join(interests)}")

    if merged_context.get("with_dog"):
        summary_parts.append("dog-friendly preference")

    if merged_context.get("with_children"):
        summary_parts.append("family context")

    return ", ".join(summary_parts)


def build_duration_fit_score(
    requested_duration_minutes: int | None,
    estimated_duration_minutes: int | None,
    time_mode: str,
) -> float | None:
    if time_mode != "explicit_budget":
        return None

    if requested_duration_minutes is None or estimated_duration_minutes is None:
        return None

    if requested_duration_minutes <= 0:
        return None

    difference = abs(requested_duration_minutes - estimated_duration_minutes)
    raw_score = 1 - (difference / requested_duration_minutes)

    return round(max(0.0, raw_score), 2)


def build_candidate_points(
    ordered_places,
    ranked_places: list[dict],
    opening_by_place_id: dict[int, dict] | None = None,
) -> list[ItineraryPointRead]:
    reasons_by_place_id: dict[int, list[str]] = {}

    for item in ranked_places:
        place = item["place"]
        reasons_by_place_id[place.id] = item.get("reasons", [])

    points: list[ItineraryPointRead] = []

    for index, place in enumerate(ordered_places, start=1):
        reasons = reasons_by_place_id.get(place.id, [])

        reason = build_place_reason(
            place=place,
            ranked_reasons=reasons,
        )

        opening_info = opening_by_place_id.get(place.id) if opening_by_place_id else None
        if opening_info and opening_info.get("is_open") is False:
            reason = f"{reason}. ⚠️ May be closed at estimated visit time"

        points.append(
            ItineraryPointRead(
                place_id=place.id,
                position=index,
                place_slug=place.slug,
                place_title=place.title,
                reason=reason,
            )
        )

    return points


def build_current_route_context(
    request: ItineraryGenerateRequest,
    ordered_places,
    route_mode: str,
    estimated_duration_minutes: int | None,
) -> CurrentRouteContextRead:
    points = [
        CurrentRoutePointRead(
            place_id=place.id,
            position=index,
            place_slug=place.slug,
            place_title=place.title,
        )
        for index, place in enumerate(ordered_places, start=1)
    ]

    return CurrentRouteContextRead(
        city_slug=request.city_slug,
        route_mode=route_mode,
        points=points,
        remaining_time_minutes=estimated_duration_minutes,
        return_to_start=request.return_to_start,
        budget_level=request.budget_level,
    )


def enrich_runtime_context(
    merged_context: dict,
    request: ItineraryGenerateRequest,
    timezone_name: str,
) -> tuple[dict, str, str]:
    time_mode = merged_context.get("time_mode") or request.time_mode or "open_duration"
    route_mode = merged_context.get("route_mode") or request.route_mode or "walk"

    merged_context["time_mode"] = time_mode
    merged_context["route_mode"] = route_mode
    merged_context["trip_start_datetime"] = request.trip_start_datetime
    merged_context["city_timezone"] = timezone_name

    if request.budget_level is not None:
        merged_context["budget_level"] = request.budget_level

    return merged_context, time_mode, route_mode


def generate_itinerary_stub(
    db: Session,
    request: ItineraryGenerateRequest,
) -> ItineraryGenerateResponse:
    parsed_intent = parse_route_intent(request.query)

    merged_context = merge_explicit_fields_and_text_constraints(
        request=request,
        parsed_intent=parsed_intent,
    )

    city = get_city_by_slug(db=db, city_slug=request.city_slug)
    timezone_name = resolve_timezone_name(
        timezone_name=None,
        city=city,
    )

    merged_context, time_mode, route_mode = enrich_runtime_context(
        merged_context=merged_context,
        request=request,
        timezone_name=timezone_name,
    )

    start_context = build_start_context_read(
        request=request,
        db=db,
    )

    candidate_places = get_candidate_places(
        db=db,
        request=request,
        merged_context=merged_context,
        start_context=start_context,
    )

    ranked_places = rank_candidate_places(
        candidate_places=candidate_places,
        merged_context=merged_context,
        start_context=start_context,
    )

    route_result = build_route_from_ranked_places(
        ranked_places=ranked_places,
        merged_context=merged_context,
        start_context=start_context,
        max_places=request.max_places or 5,
    )

    ordered_places = route_result["places"]
    estimated_duration_minutes = route_result["estimated_duration_minutes"]
    estimated_distance_km = route_result["estimated_distance_km"]

    opening_statuses = estimate_route_opening_statuses(
        places=ordered_places,
        merged_context=merged_context,
        trip_start_datetime=request.trip_start_datetime,
        timezone_name=timezone_name,
        start_context=start_context,
    )

    opening_by_place_id = {
        item["place_id"]: item for item in opening_statuses
    }

    if time_mode == "explicit_budget":
        requested_duration_minutes = merged_context.get("time_budget_minutes")
    else:
        requested_duration_minutes = None

    duration_fit_score = build_duration_fit_score(
        requested_duration_minutes=requested_duration_minutes,
        estimated_duration_minutes=estimated_duration_minutes,
        time_mode=time_mode,
    )

    points = build_candidate_points(
        ordered_places=ordered_places,
        ranked_places=ranked_places,
        opening_by_place_id=opening_by_place_id,
    )

    current_route_context = build_current_route_context(
        request=request,
        ordered_places=ordered_places,
        route_mode=route_mode,
        estimated_duration_minutes=estimated_duration_minutes,
    )

    summary = build_itinerary_summary(
        request=request,
        merged_context=merged_context,
    )

    explanation = build_route_explanation(
        merged_context=merged_context,
        ordered_places=ordered_places,
        estimated_duration_minutes=estimated_duration_minutes,
        estimated_distance_km=estimated_distance_km,
        start_context=start_context,
        requested_duration_minutes=requested_duration_minutes,
        duration_fit_score=duration_fit_score,
    )

    from services.route_generation_diagnostics.record import record_itinerary_generation

    record_itinerary_generation(
        db,
        city=city,
        request_payload={"source": "itinerary_generate", "city_slug": request.city_slug},
        ordered_places=ordered_places,
        ranked_places=ranked_places,
    )

    return ItineraryGenerateResponse(
        status="ok",
        title="Generated itinerary draft",
        summary=summary,
        time_mode=time_mode,
        requested_duration_minutes=requested_duration_minutes,
        estimated_duration_minutes=estimated_duration_minutes,
        distance_km=estimated_distance_km,
        route_mode=route_mode,
        duration_fit_score=duration_fit_score,
        start_context=start_context,
        points=points,
        current_route_context=current_route_context,
        explanation=explanation,
    )
