from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from schemas.itinerary import CurrentRouteContextRead, CurrentRoutePointRead
from schemas.itinerary_replan import (
    CurrentRouteContextInput,
    ItineraryReplanRequest,
    ItineraryReplanResponse,
    ReplannedRoutePointRead,
)
from services.itinerary_route_builder_service import build_route_from_ranked_places
from services.itinerary_scoring_service import rank_candidate_places
from services.itinerary_text_parser import parse_route_intent
from services.itinerary_time_service import (
    estimate_route_opening_statuses,
    estimate_total_route_distance_km,
    estimate_total_route_time_minutes,
    haversine_distance_km,
    is_place_open_at,
    resolve_timezone_name,
)
from services.route_eligibility import apply_route_eligible_filters, evaluate_place_route_eligibility


@dataclass
class InlineStartContext:
    lat: float
    lng: float
    source: str = "geo_device"
    accuracy_tier: str = "approximate"
    display_label: str = "Current position"
    raw_address: str | None = None
    warning_message: str | None = None


def get_city_by_slug(db: Session, city_slug: str) -> City | None:
    if db is None:
        return None

    return db.query(City).filter(City.slug == city_slug).first()


# Возвращает текущее локальное время города.
def get_city_now(city: City | None) -> datetime:
    timezone_name = resolve_timezone_name(
        timezone_name=None,
        city=city,
    )
    return datetime.now(ZoneInfo(timezone_name))


# Проверяет, открыто ли место прямо сейчас для stop insertion в replan.
# Если opening_hours нет, не режем место.
def is_place_open_for_replan(place: Place, city: City | None) -> bool:
    city_now = get_city_now(city)
    open_status = is_place_open_at(
        place=place,
        dt=city_now,
    )

    if open_status is None:
        return True

    return open_status


def build_runtime_start_context(
    current_lat: float | None,
    current_lng: float | None,
    fallback_place: Place | None = None,
) -> InlineStartContext | None:
    if current_lat is not None and current_lng is not None:
        return InlineStartContext(
            lat=current_lat,
            lng=current_lng,
            source="geo_device",
            accuracy_tier="approximate",
            display_label="Current position",
        )

    if fallback_place is not None:
        return InlineStartContext(
            lat=fallback_place.lat,
            lng=fallback_place.lng,
            source="place_id",
            accuracy_tier="precise",
            display_label=fallback_place.title,
        )

    return None


def build_place_start_context(place: Place) -> InlineStartContext:
    return InlineStartContext(
        lat=place.lat,
        lng=place.lng,
        source="place_id",
        accuracy_tier="precise",
        display_label=place.title,
    )


def load_route_places(
    db: Session,
    current_route: CurrentRouteContextInput,
) -> tuple[list[Place], list[int]]:
    ordered_points = sorted(current_route.points, key=lambda point: point.position)
    place_ids = [point.place_id for point in ordered_points]

    if not place_ids:
        return [], []

    query = db.query(Place).filter(Place.id.in_(place_ids))
    places = apply_route_eligible_filters(query).all()
    places_by_id = {place.id: place for place in places}

    ordered_places: list[Place] = []
    missing_place_ids: list[int] = []

    for place_id in place_ids:
        place = places_by_id.get(place_id)
        if place is not None:
            ordered_places.append(place)
        else:
            missing_place_ids.append(place_id)

    return ordered_places, missing_place_ids


def get_remaining_places(
    ordered_places: list[Place],
    completed_place_ids: list[int],
) -> list[Place]:
    completed_set = set(completed_place_ids)
    return [place for place in ordered_places if place.id not in completed_set]


def order_places_from_anchor(
    places: list[Place],
    anchor_lat: float | None,
    anchor_lng: float | None,
) -> list[Place]:
    if len(places) <= 1:
        return places

    if anchor_lat is None or anchor_lng is None:
        return places

    remaining_places = places.copy()
    ordered_places: list[Place] = []

    first_place = min(
        remaining_places,
        key=lambda place: haversine_distance_km(
            anchor_lat,
            anchor_lng,
            place.lat,
            place.lng,
        ),
    )

    ordered_places.append(first_place)
    remaining_places.remove(first_place)

    while remaining_places:
        current_place = ordered_places[-1]

        next_place = min(
            remaining_places,
            key=lambda place: haversine_distance_km(
                current_place.lat,
                current_place.lng,
                place.lat,
                place.lng,
            ),
        )

        ordered_places.append(next_place)
        remaining_places.remove(next_place)

    return ordered_places


def get_effective_time_budget_minutes(
    request: ItineraryReplanRequest,
) -> int | None:
    if request.new_time_budget_minutes is not None:
        return request.new_time_budget_minutes

    if request.current_route.remaining_time_minutes is not None:
        return request.current_route.remaining_time_minutes

    return None


def trim_places_to_time_budget(
    places: list[Place],
    route_mode: str,
    start_context,
    time_budget_minutes: int | None,
    city_timezone: str | None = None,
) -> list[Place]:
    if time_budget_minutes is None:
        return places

    if not places:
        return places

    merged_context = {
        "route_mode": route_mode,
        "time_mode": "explicit_budget",
        "time_budget_minutes": time_budget_minutes,
    }

    if city_timezone:
        merged_context["city_timezone"] = city_timezone

    trimmed_places = places.copy()

    while len(trimmed_places) > 1:
        estimated_minutes = estimate_total_route_time_minutes(
            places=trimmed_places,
            merged_context=merged_context,
            start_context=start_context,
        )

        if estimated_minutes <= time_budget_minutes:
            break

        trimmed_places.pop()

    return trimmed_places


def get_reason_target_categories(reason_type: str) -> list[str]:
    if reason_type in {"food_stop", "coffee_stop"}:
        return ["cafe"]

    if reason_type == "rest_stop":
        return ["walk", "park", "promenade", "viewpoint", "beach"]

    return []


def get_anchor_coordinates_for_stop_search(
    request: ItineraryReplanRequest,
    remaining_places: list[Place],
) -> tuple[float | None, float | None]:
    if request.current_lat is not None and request.current_lng is not None:
        return request.current_lat, request.current_lng

    if remaining_places:
        return remaining_places[0].lat, remaining_places[0].lng

    return None, None


def load_preferred_stop_place(
    db: Session,
    city_slug: str,
    preferred_stop_place_id: int | None,
    exclude_place_ids: set[int],
    target_categories: list[str] | None,
) -> Place | None:
    if preferred_stop_place_id is None:
        return None

    city = get_city_by_slug(db, city_slug)
    if city is None:
        return None

    query = db.query(Place).filter(Place.id == preferred_stop_place_id)
    place = apply_route_eligible_filters(query).first()

    if place is None:
        return None

    if place.id in exclude_place_ids:
        return None

    if place.city_id != city.id:
        return None

    if target_categories and place.category not in target_categories:
        return None

    if not is_place_open_for_replan(place=place, city=city):
        return None

    return place


def find_best_stop_place(
    db: Session,
    city_slug: str,
    reason_type: str,
    anchor_lat: float | None,
    anchor_lng: float | None,
    exclude_place_ids: set[int],
    budget_level: int | None = None,
) -> Place | None:
    city = get_city_by_slug(db, city_slug)
    if city is None:
        return None

    target_categories = get_reason_target_categories(reason_type)
    if not target_categories:
        return None

    query = db.query(Place).filter(
        Place.city_id == city.id,
        Place.category.in_(target_categories),
    )
    query = apply_route_eligible_filters(query)

    if budget_level is not None:
        query = query.filter(Place.price_level <= budget_level)

    places = query.all()

    candidates = [
        place
        for place in places
        if place.id not in exclude_place_ids
        and is_place_open_for_replan(place=place, city=city)
        and evaluate_place_route_eligibility(place, city=city).eligible
    ]
    if not candidates:
        return None

    if anchor_lat is None or anchor_lng is None:
        return sorted(candidates, key=lambda place: place.title.lower())[0]

    return min(
        candidates,
        key=lambda place: haversine_distance_km(
            anchor_lat,
            anchor_lng,
            place.lat,
            place.lng,
        ),
    )


def maybe_insert_stop_place(
    db: Session,
    request: ItineraryReplanRequest,
    remaining_places: list[Place],
) -> tuple[list[Place], Place | None]:
    if request.reason_type not in {"food_stop", "coffee_stop", "rest_stop"}:
        return remaining_places, None

    target_categories = get_reason_target_categories(request.reason_type)
    if not target_categories:
        return remaining_places, None

    exclude_place_ids = {place.id for place in remaining_places}
    anchor_lat, anchor_lng = get_anchor_coordinates_for_stop_search(
        request=request,
        remaining_places=remaining_places,
    )

    preferred_stop_place = load_preferred_stop_place(
        db=db,
        city_slug=request.current_route.city_slug,
        preferred_stop_place_id=request.preferred_stop_place_id,
        exclude_place_ids=exclude_place_ids,
        target_categories=target_categories,
    )
    if preferred_stop_place is not None:
        return [preferred_stop_place, *remaining_places], preferred_stop_place

    if remaining_places and remaining_places[0].category in target_categories:
        current_city = get_city_by_slug(db, request.current_route.city_slug)
        if is_place_open_for_replan(place=remaining_places[0], city=current_city):
            return remaining_places, remaining_places[0]

    stop_place = find_best_stop_place(
        db=db,
        city_slug=request.current_route.city_slug,
        reason_type=request.reason_type,
        anchor_lat=anchor_lat,
        anchor_lng=anchor_lng,
        exclude_place_ids=exclude_place_ids,
        budget_level=request.current_route.budget_level,
    )
    if stop_place is None:
        return remaining_places, None

    return [stop_place, *remaining_places], stop_place


def should_reorder_after_replan(request: ItineraryReplanRequest) -> bool:
    if request.reason_type in {
        "coffee_stop",
        "food_stop",
        "rest_stop",
        "continue_from_here",
        "custom",
    }:
        return True

    if request.user_message:
        return True

    return False


def ensure_unique_interests(interests: list[str]) -> list[str]:
    result: list[str] = []

    for interest in interests:
        if interest not in result:
            result.append(interest)

    return result


def build_replan_merged_context(
    request: ItineraryReplanRequest,
    city_timezone: str | None = None,
) -> dict:
    parsed_intent = parse_route_intent(request.user_message)

    preferences = parsed_intent.get("preferences", {})
    parsed_interests: list[str] = preferences.get("interests", []) or []

    reason_interests: list[str] = []

    if request.reason_type == "coffee_stop":
        reason_interests.append("coffee")
    elif request.reason_type == "food_stop":
        reason_interests.append("food")
    elif request.reason_type == "rest_stop":
        reason_interests.extend(["walk", "quiet"])

    interests = ensure_unique_interests([*reason_interests, *parsed_interests])

    route_mode = parsed_intent.get("route_mode") or request.current_route.route_mode
    effective_time_budget_minutes = get_effective_time_budget_minutes(request)
    time_mode = (
        "explicit_budget"
        if effective_time_budget_minutes is not None
        else "open_duration"
    )

    merged_context = {
        "route_mode": route_mode,
        "time_mode": time_mode,
        "time_budget_minutes": effective_time_budget_minutes,
        "preferences": {
            "interests": interests,
            "anti_tourist": preferences.get("anti_tourist", False),
            "pace_mode": preferences.get("pace_mode"),
        },
        "with_dog": parsed_intent.get("constraints", {}).get("with_dog", False),
        "with_children": parsed_intent.get("constraints", {}).get("with_children", False),
        "indoor_only": parsed_intent.get("constraints", {}).get("indoor_only", False),
        "outdoor_only": parsed_intent.get("constraints", {}).get("outdoor_only", False),
        "budget_level": request.current_route.budget_level,
    }

    if city_timezone:
        merged_context["city_timezone"] = city_timezone

    return merged_context


def rerank_places_for_replan(
    places: list[Place],
    request: ItineraryReplanRequest,
    start_context,
    city_timezone: str | None = None,
) -> list[Place]:
    if len(places) <= 1:
        return places

    merged_context = build_replan_merged_context(
        request=request,
        city_timezone=city_timezone,
    )

    ranked_places = rank_candidate_places(
        candidate_places=places,
        merged_context=merged_context,
        start_context=start_context,
    )

    route_result = build_route_from_ranked_places(
        ranked_places=ranked_places,
        merged_context=merged_context,
        start_context=start_context,
        max_places=len(places),
    )

    return route_result["places"]


def build_points_with_reasons(
    places: list[Place],
    request: ItineraryReplanRequest,
    opening_by_place_id: dict[int, dict] | None = None,
) -> list[ReplannedRoutePointRead]:
    points: list[ReplannedRoutePointRead] = []

    for index, place in enumerate(places, start=1):
        if index == 1 and request.reason_type == "coffee_stop":
            reason = "Добавлена ближайшая coffee stop точка."
        elif index == 1 and request.reason_type == "food_stop":
            reason = "Добавлена ближайшая food stop точка."
        elif index == 1 and request.reason_type == "rest_stop":
            reason = "Добавлена ближайшая stop point для короткой паузы."
        elif request.reason_type == "shorten_route":
            reason = "Оставлена в сокращенном остатке маршрута."
        elif request.reason_type == "continue_from_here":
            reason = "Оставлена в продолжении маршрута от текущей позиции."
        elif request.reason_type == "custom":
            reason = "Оставлена после перестроения под новый запрос."
        else:
            reason = "Оставлена в актуальном остатке маршрута."

        opening_info = opening_by_place_id.get(place.id) if opening_by_place_id else None
        if opening_info and opening_info.get("is_open") is False:
            reason = f"{reason} ⚠️ Может быть закрыто к расчетному времени визита."

        points.append(
            ReplannedRoutePointRead(
                place_id=place.id,
                position=index,
                place_slug=place.slug,
                place_title=place.title,
                reason=reason,
            )
        )

    return points


def build_replan_summary(
    request: ItineraryReplanRequest,
    points_count: int,
    missing_place_ids: list[int] | None = None,
) -> str:
    if request.reason_type == "coffee_stop":
        summary = (
            f"Маршрут перестроен с добавлением coffee stop. Осталось {points_count} точек."
        )
    elif request.reason_type == "food_stop":
        summary = (
            f"Маршрут перестроен с добавлением food stop. Осталось {points_count} точек."
        )
    elif request.reason_type == "rest_stop":
        summary = (
            f"Маршрут перестроен с добавлением stop point для паузы. Осталось {points_count} точек."
        )
    elif request.reason_type == "shorten_route":
        summary = f"Маршрут сокращен. Осталось {points_count} точек."
    elif request.reason_type == "continue_from_here":
        summary = f"Маршрут продолжен от текущей позиции. Осталось {points_count} точек."
    elif request.reason_type == "custom":
        summary = (
            f"Маршрут перестроен под новый пользовательский запрос. Осталось {points_count} точек."
        )
    else:
        summary = f"Маршрут перестроен. Осталось {points_count} точек."

    if missing_place_ids:
        summary += " Часть исходных точек маршрута не найдена и была пропущена."

    return summary


def build_replan_explanation(
    request: ItineraryReplanRequest,
    estimated_remaining_minutes: int | None,
    estimated_remaining_distance_km: float | None,
    points_count: int,
    time_budget_minutes: int | None,
    missing_place_ids: list[int] | None = None,
    has_time_warnings: bool = False,
) -> str:
    parts: list[str] = []

    if request.reason_type == "coffee_stop":
        parts.append("Маршрут перестроен с учетом запроса на остановку для кофе.")
    elif request.reason_type == "food_stop":
        parts.append("Маршрут перестроен с учетом запроса на остановку для еды.")
    elif request.reason_type == "rest_stop":
        parts.append("Маршрут перестроен с учетом запроса на паузу.")
    elif request.reason_type == "shorten_route":
        parts.append("Маршрут был сокращен по новому ограничению.")
    elif request.reason_type == "continue_from_here":
        parts.append("Маршрут продолжен от текущей позиции пользователя.")
    elif request.reason_type == "custom":
        parts.append("Маршрут перестроен под новый пользовательский запрос.")
    else:
        parts.append("Маршрут перестроен по новому запросу пользователя.")

    if request.user_message:
        parts.append("При перестроении учтен дополнительный текстовый запрос пользователя.")

    if time_budget_minutes is not None:
        parts.append(
            f"Оставшийся маршрут старается уложиться примерно в {time_budget_minutes} минут."
        )

    parts.append(f"В текущем остатке маршрута {points_count} точек.")

    if estimated_remaining_minutes is not None:
        parts.append(
            f"Оценочное оставшееся время — около {estimated_remaining_minutes} минут."
        )

    if estimated_remaining_distance_km is not None:
        parts.append(
            f"Оценочная оставшаяся дистанция — около {estimated_remaining_distance_km} км."
        )

    if has_time_warnings:
        parts.append(
            "У части точек время работы может не совпасть с расчетным временем визита."
        )

    if missing_place_ids:
        ids_text = ", ".join(str(place_id) for place_id in missing_place_ids)
        parts.append(
            f"Некоторые точки исходного маршрута не найдены в базе и были исключены: {ids_text}."
        )

    return " ".join(parts)


def build_current_route_context(
    request: ItineraryReplanRequest,
    places: list[Place],
    estimated_remaining_minutes: int | None,
) -> CurrentRouteContextRead:
    return CurrentRouteContextRead(
        city_slug=request.current_route.city_slug,
        route_mode=request.current_route.route_mode,
        points=[
            CurrentRoutePointRead(
                place_id=place.id,
                position=index,
                place_slug=place.slug,
                place_title=place.title,
            )
            for index, place in enumerate(places, start=1)
        ],
        completed_place_ids=list(request.current_route.completed_place_ids),
        remaining_time_minutes=estimated_remaining_minutes,
        return_to_start=request.current_route.return_to_start,
        budget_level=request.current_route.budget_level,
    )


def build_replan_opening_status_index(
    places: list[Place],
    merged_context: dict,
    city_timezone: str,
    start_context,
) -> dict[int, dict]:
    opening_statuses = estimate_route_opening_statuses(
        places=places,
        merged_context=merged_context,
        trip_start_datetime=None,
        timezone_name=city_timezone,
        start_context=start_context,
    )

    return {
        item["place_id"]: item
        for item in opening_statuses
    }


def replan_itinerary(
    db: Session,
    request: ItineraryReplanRequest,
) -> ItineraryReplanResponse:
    city = get_city_by_slug(
        db=db,
        city_slug=request.current_route.city_slug,
    )
    city_timezone = resolve_timezone_name(
        timezone_name=None,
        city=city,
    )

    loaded_route_places = load_route_places(
        db=db,
        current_route=request.current_route,
    )
    if isinstance(loaded_route_places, tuple):
        ordered_places, missing_place_ids = loaded_route_places
    else:
        ordered_places = loaded_route_places
        missing_place_ids = []

    remaining_places = get_remaining_places(
        ordered_places=ordered_places,
        completed_place_ids=request.current_route.completed_place_ids,
    )

    effective_time_budget_minutes = get_effective_time_budget_minutes(request)

    if request.reason_type == "shorten_route" and effective_time_budget_minutes is None:
        points = build_points_with_reasons(
            places=remaining_places,
            request=request,
        )
        current_route_context = build_current_route_context(
            request=request,
            places=remaining_places,
            estimated_remaining_minutes=None,
        )

        return ItineraryReplanResponse(
            status="ok",
            title="Replanned itinerary",
            summary=(
                f"Маршрут не был сокращен: не задан time budget. "
                f"Осталось {len(points)} точек."
            ),
            estimated_remaining_minutes=None,
            estimated_remaining_distance_km=estimate_total_route_distance_km(
                places=remaining_places,
                start_context=None,
            ),
            points=points,
            current_route_context=current_route_context,
            explanation=(
                "Сценарий shorten_route требует time budget. "
                "Передай new_time_budget_minutes или remaining_time_minutes в current_route. "
                + build_replan_explanation(
                    request=request,
                    estimated_remaining_minutes=None,
                    estimated_remaining_distance_km=None,
                    points_count=len(points),
                    time_budget_minutes=None,
                    missing_place_ids=missing_place_ids,
                )
            ),
        )

    fallback_place = remaining_places[0] if remaining_places else None
    runtime_start_context = build_runtime_start_context(
        current_lat=request.current_lat,
        current_lng=request.current_lng,
        fallback_place=fallback_place,
    )

    if should_reorder_after_replan(request):
        remaining_places = order_places_from_anchor(
            places=remaining_places,
            anchor_lat=request.current_lat,
            anchor_lng=request.current_lng,
        )

    remaining_places, inserted_stop_place = maybe_insert_stop_place(
        db=db,
        request=request,
        remaining_places=remaining_places,
    )

    if inserted_stop_place is not None:
        tail_places = [
            place for place in remaining_places if place.id != inserted_stop_place.id
        ]
        tail_start_context = build_place_start_context(inserted_stop_place)

        reranked_tail = rerank_places_for_replan(
            places=tail_places,
            request=request,
            start_context=tail_start_context,
            city_timezone=city_timezone,
        )

        remaining_places = [inserted_stop_place, *reranked_tail]

    elif should_reorder_after_replan(request):
        remaining_places = rerank_places_for_replan(
            places=remaining_places,
            request=request,
            start_context=runtime_start_context,
            city_timezone=city_timezone,
        )

    if effective_time_budget_minutes is not None:
        remaining_places = trim_places_to_time_budget(
            places=remaining_places,
            route_mode=request.current_route.route_mode,
            start_context=runtime_start_context,
            time_budget_minutes=effective_time_budget_minutes,
            city_timezone=city_timezone,
        )

    merged_context = {
        "route_mode": request.current_route.route_mode,
        "time_mode": (
            "explicit_budget"
            if effective_time_budget_minutes is not None
            else "open_duration"
        ),
        "time_budget_minutes": effective_time_budget_minutes,
        "city_timezone": city_timezone,
    }

    estimated_remaining_minutes = estimate_total_route_time_minutes(
        places=remaining_places,
        merged_context=merged_context,
        start_context=runtime_start_context,
    )
    estimated_remaining_distance_km = estimate_total_route_distance_km(
        places=remaining_places,
        start_context=runtime_start_context,
    )

    opening_by_place_id = build_replan_opening_status_index(
        places=remaining_places,
        merged_context=merged_context,
        city_timezone=city_timezone,
        start_context=runtime_start_context,
    )

    has_time_warnings = any(
        item.get("is_open") is False
        for item in opening_by_place_id.values()
    )

    points = build_points_with_reasons(
        places=remaining_places,
        request=request,
        opening_by_place_id=opening_by_place_id,
    )

    summary = build_replan_summary(
        request=request,
        points_count=len(points),
        missing_place_ids=missing_place_ids,
    )
    explanation = build_replan_explanation(
        request=request,
        estimated_remaining_minutes=estimated_remaining_minutes,
        estimated_remaining_distance_km=estimated_remaining_distance_km,
        points_count=len(points),
        time_budget_minutes=effective_time_budget_minutes,
        missing_place_ids=missing_place_ids,
        has_time_warnings=has_time_warnings,
    )
    current_route_context = build_current_route_context(
        request=request,
        places=remaining_places,
        estimated_remaining_minutes=estimated_remaining_minutes,
    )

    return ItineraryReplanResponse(
        status="ok",
        title="Replanned itinerary",
        summary=summary,
        estimated_remaining_minutes=estimated_remaining_minutes,
        estimated_remaining_distance_km=estimated_remaining_distance_km,
        points=points,
        current_route_context=current_route_context,
        explanation=explanation,
    )