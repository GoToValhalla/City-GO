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

    existing_place_ids = {place.id for place in selected_places}
    selected_categories = get_selected_categories(selected_places)

    for item in ranked_places:
        candidate_place = item["place"]

        if candidate_place.id in existing_place_ids:
            continue

        # Ищем именно новую категорию, чтобы маршрут не выглядел однотипным.
        if candidate_place.category in selected_categories:
            continue

        if not can_add_place_with_basic_diversity(
            selected_places=selected_places,
            candidate_place=candidate_place,
        ):
            continue

        if not can_add_place_with_time_budget(
            selected_places=selected_places,
            candidate_place=candidate_place,
            merged_context=merged_context,
            start_context=start_context,
        ):
            continue

        return [*selected_places, candidate_place]

    return selected_places


# Пытается сначала покрыть ключевые категории маршрута,
# а уже потом добирать дополнительные точки.
def select_required_coverage_places(
    ranked_places: list[dict],
    merged_context: dict,
    max_places: int,
    start_context,
) -> list[Place]:
    selected_places: list[Place] = []
    required_categories = get_required_route_categories(merged_context)

    if not required_categories:
        return selected_places

    for required_category in required_categories:
        if len(selected_places) >= max_places:
            break

        if is_required_category_already_covered(selected_places, required_category):
            continue

        for item in ranked_places:
            candidate_place = item["place"]

            if candidate_place.category != required_category:
                continue

            if not can_add_place_with_basic_diversity(
                selected_places=selected_places,
                candidate_place=candidate_place,
            ):
                continue

            if not can_add_place_with_time_budget(
                selected_places=selected_places,
                candidate_place=candidate_place,
                merged_context=merged_context,
                start_context=start_context,
            ):
                continue

            selected_places.append(candidate_place)
            break

    return selected_places


# Подрезает маршрут, если он слишком сильно вылез за желаемый time budget.
# Убираем хвост после ordering, пока не вернемся в допустимый диапазон.
def trim_route_to_time_budget(
    ordered_places: list[Place],
    merged_context: dict,
    start_context,
) -> list[Place]:
    requested_time_budget = get_requested_time_budget_minutes(merged_context)

    if not is_explicit_time_budget(merged_context) or requested_time_budget is None:
        return ordered_places

    tolerance_minutes = get_time_budget_tolerance_minutes(requested_time_budget)
    max_allowed_minutes = requested_time_budget + tolerance_minutes

    trimmed_places = ordered_places.copy()

    # Мягко режем хвост, пока маршрут не перестанет выходить за допустимую рамку.
    while len(trimmed_places) > 1:
        estimated_minutes = get_route_minutes(
            places=trimmed_places,
            merged_context=merged_context,
            start_context=start_context,
        )

        if estimated_minutes <= max_allowed_minutes:
            break

        trimmed_places.pop()

    return trimmed_places


# Ищет лучший вариант расширения маршрута, если он слишком короткий относительно budget.
def choose_best_expansion_candidate(
    expanded_places: list[Place],
    ranked_places: list[dict],
    merged_context: dict,
    max_places: int,
    start_context,
) -> list[Place]:
    requested_time_budget = get_requested_time_budget_minutes(merged_context)
    if requested_time_budget is None:
        return expanded_places

    tolerance_minutes = get_time_budget_tolerance_minutes(requested_time_budget)
    max_allowed_minutes = requested_time_budget + tolerance_minutes
    existing_place_ids = {place.id for place in expanded_places}

    best_ordered_places = expanded_places
    best_gap = abs(
        requested_time_budget
        - get_route_minutes(
            places=expanded_places,
            merged_context=merged_context,
            start_context=start_context,
        )
    )

    for item in ranked_places:
        candidate_place = item["place"]

        if candidate_place.id in existing_place_ids:
            continue

        if len(expanded_places) >= max_places:
            break

        if not can_add_place_with_basic_diversity(
            selected_places=expanded_places,
            candidate_place=candidate_place,
        ):
            continue

        tentative_places = [*expanded_places, candidate_place]
        tentative_ordered_places = order_route_points(
            selected_places=tentative_places,
            start_context=start_context,
        )

        tentative_minutes = get_route_minutes(
            places=tentative_ordered_places,
            merged_context=merged_context,
            start_context=start_context,
        )

        if tentative_minutes > max_allowed_minutes:
            continue

        tentative_gap = abs(requested_time_budget - tentative_minutes)

        # Берем вариант, который ближе к budget,
        # а не просто первый попавшийся допустимый.
        if tentative_gap < best_gap:
            best_ordered_places = tentative_ordered_places
            best_gap = tentative_gap

    return best_ordered_places


# Пытается расширить маршрут, если он слишком короткий относительно явного time budget.
# Добавление новой точки тоже проверяем через ordered route.
def expand_route_if_needed(
    ordered_places: list[Place],
    ranked_places: list[dict],
    merged_context: dict,
    max_places: int,
    start_context,
) -> list[Place]:
    requested_time_budget = get_requested_time_budget_minutes(merged_context)

    if not is_explicit_time_budget(merged_context) or requested_time_budget is None:
        return ordered_places

    expanded_places = ordered_places.copy()
    tolerance_minutes = get_time_budget_tolerance_minutes(requested_time_budget)

    if len(expanded_places) >= max_places:
        return expanded_places

    current_minutes = get_route_minutes(
        places=expanded_places,
        merged_context=merged_context,
        start_context=start_context,
    )

    # Если уже близко к бюджету, не раздуваем маршрут.
    if current_minutes >= requested_time_budget - tolerance_minutes:
        return expanded_places

    return choose_best_expansion_candidate(
        expanded_places=expanded_places,
        ranked_places=ranked_places,
        merged_context=merged_context,
        max_places=max_places,
        start_context=start_context,
    )


# Выбирает осмысленный набор places для маршрута.
# Сначала стараемся покрыть ключевые категории по интенту,
# затем добираем дополнительные точки по ранжированию.
def select_route_places(
    ranked_places: list[dict],
    merged_context: dict,
    max_places: int,
    start_context,
) -> list[Place]:
    selected_places = select_required_coverage_places(
        ranked_places=ranked_places,
        merged_context=merged_context,
        max_places=max_places,
        start_context=start_context,
    )

    selected_place_ids = {place.id for place in selected_places}

    for item in ranked_places:
        candidate_place = item["place"]

        if candidate_place.id in selected_place_ids:
            continue

        if not can_add_place_with_basic_diversity(
            selected_places=selected_places,
            candidate_place=candidate_place,
        ):
            continue

        if not can_add_place_with_time_budget(
            selected_places=selected_places,
            candidate_place=candidate_place,
            merged_context=merged_context,
            start_context=start_context,
        ):
            continue

        selected_places.append(candidate_place)
        selected_place_ids.add(candidate_place.id)

        if len(selected_places) >= max_places:
            break

    if not selected_places and ranked_places:
        selected_places.append(ranked_places[0]["place"])

    # Мягкий fallback на разнообразие маршрута.
    selected_places = add_best_diversity_fallback_place(
        selected_places=selected_places,
        ranked_places=ranked_places,
        merged_context=merged_context,
        start_context=start_context,
        max_places=max_places,
    )

    return selected_places


# Возвращает локальный trip start в таймзоне города.
# Если trip_start_datetime не задан, time-aware pass 2 не выполняем.
def get_local_trip_start_datetime(merged_context: dict) -> datetime | None:
    trip_start_datetime = merged_context.get("trip_start_datetime")
    if trip_start_datetime is None:
        return None

    timezone_name = merged_context.get("city_timezone") or "UTC"
    city_tz = ZoneInfo(timezone_name)

    if trip_start_datetime.tzinfo is None:
        return trip_start_datetime.replace(tzinfo=city_tz)

    return trip_start_datetime.astimezone(city_tz)


# Строит индекс opening statuses по place_id для уже собранного маршрута.
def build_opening_status_index(
    places: list[Place],
    merged_context: dict,
    start_context,
) -> dict[int, dict]:
    trip_start_datetime = get_local_trip_start_datetime(merged_context)
    if trip_start_datetime is None:
        return {}

    timezone_name = merged_context.get("city_timezone") or "UTC"

    opening_statuses = estimate_route_opening_statuses(
        places=places,
        merged_context=merged_context,
        trip_start_datetime=trip_start_datetime,
        timezone_name=timezone_name,
        start_context=start_context,
    )

    return {
        item["place_id"]: item
        for item in opening_statuses
    }


# Ищет замену для точки, которая закрыта в своем реальном arrival time.
# Это второй time-aware проход:
# - сначала строим маршрут грубо
# - потом проверяем реальные arrival times
# - если точка закрыта, пытаемся заменить ее резервным кандидатом
def choose_replacement_for_closed_place(
    ordered_places: list[Place],
    ranked_places: list[dict],
    replace_index: int,
    merged_context: dict,
    start_context,
) -> Place | None:
    existing_place_ids = {place.id for place in ordered_places}
    current_place = ordered_places[replace_index]

    # Сначала пробуем найти гарантированно открытую замену.
    # Если не нашли, потом пробуем вариант с неизвестными opening_hours.
    best_unknown_candidate: Place | None = None

    for item in ranked_places:
        candidate_place = item["place"]

        if candidate_place.id == current_place.id:
            continue

        if candidate_place.id in existing_place_ids:
            continue

        if not can_replace_place_with_basic_diversity(
            selected_places=ordered_places,
            replace_index=replace_index,
            candidate_place=candidate_place,
        ):
            continue

        tentative_places = ordered_places.copy()
        tentative_places[replace_index] = candidate_place

        if not route_fits_time_budget(
            places=tentative_places,
            merged_context=merged_context,
            start_context=start_context,
        ):
            continue

        opening_index = build_opening_status_index(
            places=tentative_places,
            merged_context=merged_context,
            start_context=start_context,
        )
        opening_info = opening_index.get(candidate_place.id)

        # Если time-aware данных нет — не делаем автоматический swap.
        if opening_info is None:
            continue

        if opening_info.get("is_open") is True:
            return candidate_place

        # Неизвестные opening_hours лучше закрытых,
        # но хуже гарантированно открытых.
        if opening_info.get("is_open") is None and best_unknown_candidate is None:
            best_unknown_candidate = candidate_place

    return best_unknown_candidate


# Выполняет второй проход по уже собранному маршруту:
# проверяет реальные arrival times и пытается локально заменить
# точки, которые закрыты к моменту визита.
def apply_time_aware_opening_pass(
    ordered_places: list[Place],
    ranked_places: list[dict],
    merged_context: dict,
    start_context,
) -> list[Place]:
    trip_start_datetime = get_local_trip_start_datetime(merged_context)
    if trip_start_datetime is None:
        return ordered_places

    adjusted_places = ordered_places.copy()

    for index in range(len(adjusted_places)):
        opening_index = build_opening_status_index(
            places=adjusted_places,
            merged_context=merged_context,
            start_context=start_context,
        )
        opening_info = opening_index.get(adjusted_places[index].id)

        if opening_info is None:
            continue

        # Только реально закрытые точки пытаемся менять.
        # Unknown не трогаем, чтобы не выкидывать хорошие места из-за неполных данных.
        if opening_info.get("is_open") is not False:
            continue

        replacement = choose_replacement_for_closed_place(
            ordered_places=adjusted_places,
            ranked_places=ranked_places,
            replace_index=index,
            merged_context=merged_context,
            start_context=start_context,
        )

        if replacement is not None:
            adjusted_places[index] = replacement

    return adjusted_places


# Собирает маршрут:
# 1) выбирает релевантные точки,
# 2) старается покрыть ключевые категории по интенту,
# 3) упорядочивает их от старта,
# 4) подрезает по time budget,
# 5) пытается расширить маршрут, если он слишком короткий,
# 6) делает второй time-aware проход по opening hours,
# 7) считает длительность и дистанцию уже от реального старта.
def build_route_from_ranked_places(
    ranked_places: list[dict],
    merged_context: dict,
    start_context,
    max_places: int,
) -> dict:
    selected_places = select_route_places(
        ranked_places=ranked_places,
        merged_context=merged_context,
        max_places=max_places,
        start_context=start_context,
    )

    ordered_places = order_route_points(
        selected_places=selected_places,
        start_context=start_context,
    )

    ordered_places = trim_route_to_time_budget(
        ordered_places=ordered_places,
        merged_context=merged_context,
        start_context=start_context,
    )

    expanded_places = expand_route_if_needed(
        ordered_places=ordered_places,
        ranked_places=ranked_places,
        merged_context=merged_context,
        max_places=max_places,
        start_context=start_context,
    )

    # Переупорядочиваем только если состав реально поменялся.
    if [place.id for place in expanded_places] != [place.id for place in ordered_places]:
        ordered_places = order_route_points(
            selected_places=expanded_places,
            start_context=start_context,
        )

    # Второй проход: проверяем точки относительно их реального visit_time.
    ordered_places = apply_time_aware_opening_pass(
        ordered_places=ordered_places,
        ranked_places=ranked_places,
        merged_context=merged_context,
        start_context=start_context,
    )

    estimated_duration_minutes = estimate_total_route_time_minutes(
        places=ordered_places,
        merged_context=merged_context,
        start_context=start_context,
    )
    estimated_distance_km = estimate_total_route_distance_km(
        places=ordered_places,
        start_context=start_context,
    )

    return {
        "places": ordered_places,
        "estimated_duration_minutes": estimated_duration_minutes,
        "estimated_distance_km": estimated_distance_km,
    }
