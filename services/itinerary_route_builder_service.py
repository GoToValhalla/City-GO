"""LEGACY ITINERARY ROUTE BUILDER HELPERS.

Status: part of the old `/routes/generate` itinerary stack.

Active route-generation source of truth:
- `services.route_builder_flow`
- user route build/draft/session services.

Rules:
- Do not add new route product behavior here.
- Keep only for old itinerary endpoint compatibility until consumers migrate.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from models.place import Place
from services.itinerary_time_service import (
    estimate_route_opening_statuses,
    estimate_total_route_distance_km,
    estimate_total_route_time_minutes,
    haversine_distance_km,
)


# Возвращает координаты старта маршрута, если они есть в start_context.
def get_start_coordinates(start_context) -> tuple[float, float] | None:
    if start_context is None:
        return None

    if getattr(start_context, "source", None) == "invalid":
        return None

    if getattr(start_context, "lat", None) is None or getattr(start_context, "lng", None) is None:
        return None

    return start_context.lat, start_context.lng


# Проверяет, работает ли маршрут в режиме явного time budget.
def is_explicit_time_budget(merged_context: dict) -> bool:
    return (
        merged_context.get("time_mode", "open_duration") == "explicit_budget"
        and merged_context.get("time_budget_minutes") is not None
    )


# Возвращает requested time budget из merged_context.
def get_requested_time_budget_minutes(merged_context: dict) -> int | None:
    return merged_context.get("time_budget_minutes")


# Пытается определить, стоит ли добавлять новую точку в маршрут.
# Это первый фильтр разнообразия: не хотим собирать маршрут из 5 однотипных точек подряд.
def can_add_place_with_basic_diversity(
    selected_places: list[Place],
    candidate_place: Place,
) -> bool:
    if not selected_places:
        return True

    same_category_count = sum(
        1 for place in selected_places if place.category == candidate_place.category
    )

    if same_category_count >= 2:
        return False

    return True


# Проверяет diversity при попытке заменить уже выбранную точку.
def can_replace_place_with_basic_diversity(
    selected_places: list[Place],
    replace_index: int,
    candidate_place: Place,
) -> bool:
    tentative_places = [
        place
        for index, place in enumerate(selected_places)
        if index != replace_index
    ]

    return can_add_place_with_basic_diversity(
        selected_places=tentative_places,
        candidate_place=candidate_place,
    )


# Возвращает мягкий допуск к лимиту времени.
def get_time_budget_tolerance_minutes(requested_time_budget: int | None) -> int:
    if requested_time_budget is None:
        return 10

    if requested_time_budget <= 90:
        return 10

    if requested_time_budget <= 180:
        return 15

    return 20


# Упорядочивает точки маршрута от стартовой точки или от первой лучшей точки.
# Используем nearest-neighbor подход, чтобы маршрут выглядел естественнее.
def order_route_points(
    selected_places: list[Place],
    start_context,
) -> list[Place]:
    if len(selected_places) <= 1:
        return selected_places

    remaining_places = selected_places.copy()
    ordered_places: list[Place] = []

    start_coordinates = get_start_coordinates(start_context)

    if start_coordinates is not None:
        start_lat, start_lng = start_coordinates

        # Первая точка — ближайшая к старту.
        first_place = min(
            remaining_places,
            key=lambda place: haversine_distance_km(
                start_lat,
                start_lng,
                place.lat,
                place.lng,
            ),
        )
    else:
        first_place = remaining_places[0]

    ordered_places.append(first_place)
    remaining_places.remove(first_place)

    # Дальше жадный nearest-neighbor.
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


# Считает длительность маршрута уже после ordering от старта.
# Это важнее для честного time budget, чем считать время по сырому списку.
def estimate_ordered_route_minutes(
    places: list[Place],
    merged_context: dict,
    start_context,
) -> int:
    ordered_places = order_route_points(
        selected_places=places,
        start_context=start_context,
    )

    return estimate_total_route_time_minutes(
        places=ordered_places,
        merged_context=merged_context,
        start_context=start_context,
    )


# Проверяет, можно ли добавить точку в маршрут с учетом time budget.
# Важно: budget проверяем уже после ordering от старта.
def can_add_place_with_time_budget(
    selected_places: list[Place],
    candidate_place: Place,
    merged_context: dict,
    start_context,
) -> bool:
    requested_time_budget = get_requested_time_budget_minutes(merged_context)
    tolerance_minutes = get_time_budget_tolerance_minutes(requested_time_budget)

    if not is_explicit_time_budget(merged_context) or requested_time_budget is None:
        return True

    tentative_places = [*selected_places, candidate_place]
    tentative_minutes = estimate_ordered_route_minutes(
        places=tentative_places,
        merged_context=merged_context,
        start_context=start_context,
    )

    return tentative_minutes <= requested_time_budget + tolerance_minutes


# Проверяет, помещается ли уже собранный маршрут в time budget.
def route_fits_time_budget(
    places: list[Place],
    merged_context: dict,
    start_context,
) -> bool:
    requested_time_budget = get_requested_time_budget_minutes(merged_context)
    tolerance_minutes = get_time_budget_tolerance_minutes(requested_time_budget)

    if not is_explicit_time_budget(merged_context) or requested_time_budget is None:
        return True

    estimated_minutes = estimate_total_route_time_minutes(
        places=places,
        merged_context=merged_context,
        start_context=start_context,
    )

    return estimated_minutes <= requested_time_budget + tolerance_minutes


# Определяет, какие типы точек важно покрыть по интенту пользователя.
def get_required_route_categories(merged_context: dict) -> list[str]:
    preferences = merged_context.get("preferences", {})
    interests: list[str] = preferences.get("interests", [])

    required_categories: list[str] = []

    if "coffee" in interests or "food" in interests:
        required_categories.append("cafe")

    if "walk" in interests or "sea" in interests or "quiet" in interests:
        required_categories.append("walk")

    return required_categories


# Проверяет, покрыта ли уже обязательная категория маршрута.
def is_required_category_already_covered(
    selected_places: list[Place],
    required_category: str,
) -> bool:
    return any(place.category == required_category for place in selected_places)


# Возвращает уже выбранные категории.
def get_selected_categories(selected_places: list[Place]) -> set[str]:
    return {place.category for place in selected_places}


# Унифицированный хелпер для оценки времени маршрута.
def get_route_minutes(
    places: list[Place],
    merged_context: dict,
    start_context,
) -> int:
    return estimate_total_route_time_minutes(
        places=places,
        merged_context=merged_context,
        start_context=start_context,
    )


# Если рядом мало сценарного разнообразия,
# добираем лучшую доступную точку новой категории.
def add_best_diversity_fallback_place(
    selected_places: list[Place],
    ranked_places: list[dict],
    merged_context: dict,
    start_context,
    max_places: int,
) -> list[Place]:
    if len(selected_places) >= max_places:
        return selected_places
