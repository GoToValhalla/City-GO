"""LEGACY ITINERARY SCORING SERVICE.

Status: part of the old `/routes/generate` itinerary stack.

Active scoring source of truth:
- `services.scoring_service`
- `services.route_quality_score`
- `services.route_builder_flow`

Rules:
- Do not add new scoring behavior here.
- Keep only for old itinerary endpoint compatibility until consumers migrate.
"""

from models.place import Place
from services.itinerary_time_estimator import haversine_distance_km
from services.itinerary_time_service import is_place_open_at


# Базовый вес для любой валидной точки.
BASE_SCORE = 1.0

# Вес близости к старту.
DISTANCE_WEIGHT = 0.8

# Вес совпадения с интересами пользователя.
INTEREST_WEIGHT = 1.2

# Вес контекстных бонусов.
CONTEXT_WEIGHT = 0.6

# Вес anti-tourist сигнала.
ANTI_TOURIST_WEIGHT = 0.4


# Маппинг интересов пользователя в категории мест.
def build_place_text_blob(place) -> str:
    """
    Собирает одну строку в нижнем регистре из полей места для текстового матчинга и тестов.
    """
    parts = [
        str(getattr(place, "title", "") or ""),
        str(getattr(place, "short_description", "") or ""),
        str(getattr(place, "address", "") or ""),
        str(getattr(place, "category", "") or ""),
    ]
    return " ".join(parts).strip().casefold()


INTEREST_TO_CATEGORIES = {
    "coffee": {"cafe"},
    "food": {"cafe", "restaurant", "market"},
    "sea": {"walk", "park", "viewpoint"},
    "walk": {"walk", "park", "viewpoint"},
    "quiet": {"walk", "park"},
    "museum": {"museum", "gallery"},
    "architecture": {"landmark", "church", "museum", "gallery"},
    "romantic": {"walk", "viewpoint", "restaurant"},
}


# Нормализует расстояние в мягкий score.
# Чем ближе точка к старту, тем выше бонус.
def get_distance_score(place: Place, start_context) -> float:
    distance_km = get_distance_from_start_km(
        place=place,
        start_context=start_context,
    )
    if distance_km is None:
        return 0.0

    if distance_km <= 0.5:
        return 1.0

    if distance_km <= 1.5:
        return 0.7

    if distance_km <= 3.0:
        return 0.4

    if distance_km <= 5.0:
        return 0.2

    return 0.0


def get_distance_from_start_km(place: Place, start_context) -> float | None:
    if not start_context:
        return None

    if getattr(start_context, "source", None) == "invalid":
        return None

    start_lat = getattr(start_context, "lat", None)
    start_lng = getattr(start_context, "lng", None)

    if start_lat is None or start_lng is None:
        return None

    return haversine_distance_km(
        start_lat,
        start_lng,
        place.lat,
        place.lng,
    )


def score_place_start_distance_fit(place: Place, start_context) -> tuple[float, list[str]]:
    distance_km = get_distance_from_start_km(
        place=place,
        start_context=start_context,
    )
    if distance_km is None:
        return 0.0, []

    if distance_km <= 1.5:
        return 0.8, ["Close to start point"]

    if distance_km >= 5.0:
        return -0.8, ["Far from start point"]

    return 0.0, []


# Считает score по интересам пользователя.
def get_interest_score(place: Place, merged_context: dict) -> float:
    interests = merged_context.get("preferences", {}).get("interests", [])
    if not interests:
        return 0.0

    score = 0.0

    for interest in interests:
        mapped_categories = INTEREST_TO_CATEGORIES.get(interest, set())

        if place.category in mapped_categories:
            score += 1.0

    return score


# Считает context-aware score:
# with_dog / with_children / indoor_only / outdoor_only / budget.
def get_context_score(place: Place, merged_context: dict) -> float:
    score = 0.0

    if merged_context.get("with_dog"):
        tags = getattr(place, "tags", None) or []
        if "dog" in tags or "dog_friendly" in tags:
            score += 0.5

        if place.category in {"walk", "park"}:
            score += 0.3

    if merged_context.get("with_children"):
        if place.category in {"park", "museum", "walk"}:
            score += 0.4

    if merged_context.get("indoor_only"):
        if place.category in {"museum", "gallery", "cafe", "restaurant", "church"}:
            score += 0.4

    if merged_context.get("outdoor_only"):
        if place.category in {"walk", "park", "viewpoint"}:
            score += 0.4

    budget_level = merged_context.get("budget_level")
    if budget_level is not None and place.price_level is not None:
        if place.price_level <= budget_level:
            score += 0.3
        else:
            score -= 0.6

    return score


# Считает anti-tourist бонус.
# Пока это грубая эвристика:
# - дешевые точки скорее локальные
# - walk/park тоже скорее подходят под anti-tourist сценарий
def get_anti_tourist_score(place: Place, merged_context: dict) -> float:
    if not merged_context.get("preferences", {}).get("anti_tourist"):
        return 0.0

    score = 0.0

    if place.price_level is not None and place.price_level <= 1:
        score += 0.5

    if place.category in {"walk", "park", "market"}:
        score += 0.4

    return score


# Дает штраф, если точка, скорее всего, закрыта в момент старта маршрута.
# Это не жесткий фильтр: мы просто понижаем место в ранжировании.
def get_opening_hours_penalty(place: Place, merged_context: dict) -> float:
    trip_start_datetime = merged_context.get("trip_start_datetime")

    if trip_start_datetime is None:
        return 0.0

    is_open = is_place_open_at(
        place=place,
        dt=trip_start_datetime,
    )

    if is_open is None:
        return 0.0

    if is_open is False:
        return -1.5

    return 0.0


# Основная функция скоринга одной точки.
# Возвращает итоговый score и список reason-кодов.
def score_place(
    place: Place,
    merged_context: dict,
    start_context,
) -> dict:
    reasons: list[str] = []
    total_score = BASE_SCORE

    distance_score = get_distance_score(
        place=place,
        start_context=start_context,
    )
    total_score += distance_score * DISTANCE_WEIGHT
    if distance_score > 0:
        reasons.append("close_to_start")

    start_fit_score, start_fit_reasons = score_place_start_distance_fit(
        place=place,
        start_context=start_context,
    )
    total_score += start_fit_score
    reasons.extend(start_fit_reasons)

    interest_score = get_interest_score(
        place=place,
        merged_context=merged_context,
    )
    total_score += interest_score * INTEREST_WEIGHT
    if interest_score > 0:
        reasons.append("matches_interest")

    context_score = get_context_score(
        place=place,
        merged_context=merged_context,
    )
    total_score += context_score * CONTEXT_WEIGHT
    if context_score > 0:
        reasons.append("fits_context")

    budget_level = merged_context.get("budget_level")
    price_level = getattr(place, "price_level", None)
    if budget_level is not None and price_level is not None and price_level > budget_level:
        reasons.append("Price level is above budget preference")

    anti_tourist_score = get_anti_tourist_score(
        place=place,
        merged_context=merged_context,
    )
    total_score += anti_tourist_score * ANTI_TOURIST_WEIGHT
    if anti_tourist_score > 0:
        reasons.append("local_spot")

    opening_penalty = get_opening_hours_penalty(
        place=place,
        merged_context=merged_context,
    )
    total_score += opening_penalty
    if opening_penalty < 0:
        reasons.append("likely_closed")

    return {
        "place": place,
        "score": total_score,
        "reasons": reasons,
    }


# Ранжирует candidate places по score.
def rank_candidate_places(
    candidate_places: list[Place],
    merged_context: dict,
    start_context,
) -> list[dict]:
    ranked: list[dict] = []

    for place in candidate_places:
        item = score_place(
            place=place,
            merged_context=merged_context,
            start_context=start_context,
        )

        reasons = item["reasons"] or ["Selected as a generally suitable place candidate"]
        ranked.append(
            {
                "place": place,
                "score": item["score"],
                "reasons": reasons,
            }
        )

    ranked.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    return ranked
