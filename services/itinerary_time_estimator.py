from math import asin, cos, radians, sin, sqrt

from models.place import Place


# Скорость пешего темпа в км/ч.
PACE_SPEED_KMH: dict[str, float] = {
    "fast": 4.5,
    "normal": 4.0,
    "slow": 3.2,
}


# Профили транспортных режимов.
# speed_kmh:
# - для walk не используем, там скорость считается отдельно через pace/context
# - для остальных режимов это эффективная городская скорость, а не идеальная
# overhead_min:
# - постоянная надбавка на ожидание/посадку/парковку/старт сегмента
# min_transfer:
# - минимально правдоподобное время короткого перемещения
TRANSPORT_PROFILES: dict[str, dict[str, float | None]] = {
    "walk": {
        "speed_kmh": None,
        "overhead_min": 0,
        "min_transfer": 3,
    },
    "public_transport": {
        "speed_kmh": 18.0,
        "overhead_min": 7,
        "min_transfer": 10,
    },
    "car": {
        "speed_kmh": 25.0,
        "overhead_min": 5,
        "min_transfer": 5,
    },
    "bike": {
        "speed_kmh": 12.0,
        "overhead_min": 1,
        "min_transfer": 3,
    },
    "mixed": {
        # mixed = walk-first + короткие транспортные сегменты
        "speed_kmh": 10.0,
        "overhead_min": 4,
        "min_transfer": 5,
    },
}


# Базовое рекомендованное время пребывания на точке в минутах.
# Если у точки заполнен average_visit_duration_minutes, используем его как source of truth.
PLACE_DWELL_MINUTES: dict[str, int] = {
    "cafe": 30,
    "restaurant": 50,
    "bar": 35,
    "museum": 75,
    "gallery": 45,
    "park": 30,
    "walk": 25,
    "viewpoint": 15,
    "market": 30,
    "shop": 20,
    "landmark": 15,
    "church": 20,
    "monument": 10,
    "entertainment": 60,
    "sport": 60,
}

DEFAULT_DWELL_MINUTES = 20


# Считает расстояние между двумя координатами по формуле haversine.
# Возвращает расстояние в километрах.
def haversine_distance_km(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    earth_radius_km = 6371.0

    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng / 2) ** 2
    )
    c = 2 * asin(sqrt(a))

    return earth_radius_km * c


# Возвращает темп маршрута из merged_context.
# Если темп не найден — используем normal.
def get_pace_mode(merged_context: dict) -> str:
    preferences = merged_context.get("preferences", {})
    pace_mode = preferences.get("pace_mode")

    if pace_mode in PACE_SPEED_KMH:
        return pace_mode

    return "normal"


# Возвращает скорость пешего движения с учетом темпа и контекста пользователя.
def get_effective_walk_speed_kmh(merged_context: dict) -> float:
    pace_mode = get_pace_mode(merged_context)
    speed = PACE_SPEED_KMH.get(pace_mode, 4.0)

    if merged_context.get("with_dog"):
        speed *= 0.90

    if merged_context.get("with_children"):
        speed *= 0.85

    return speed


# Возвращает скорость движения на велосипеде.
# Здесь тоже учитываем детей/собаку, потому что это заметно влияет на реальный темп.
def get_effective_bike_speed_kmh(merged_context: dict) -> float:
    profile = TRANSPORT_PROFILES["bike"]
    speed = float(profile["speed_kmh"] or 12.0)

    if merged_context.get("with_children"):
        speed *= 0.75

    if merged_context.get("with_dog"):
        speed *= 0.85

    return speed


# Возвращает эффективную скорость для конкретного режима.
def get_effective_speed_kmh(
    route_mode: str,
    merged_context: dict,
) -> float:
    if route_mode == "walk":
        return get_effective_walk_speed_kmh(merged_context)

    if route_mode == "bike":
        return get_effective_bike_speed_kmh(merged_context)

    profile = TRANSPORT_PROFILES.get(route_mode) or TRANSPORT_PROFILES["walk"]
    return float(profile["speed_kmh"] or get_effective_walk_speed_kmh(merged_context))


# Единая функция расчета времени трансфера.
# Используется и между точками, и от старта до первой точки.
def _compute_transfer_minutes(
    distance_km: float,
    route_mode: str,
    merged_context: dict,
) -> int:
    profile = TRANSPORT_PROFILES.get(route_mode) or TRANSPORT_PROFILES["walk"]

    speed_kmh = get_effective_speed_kmh(
        route_mode=route_mode,
        merged_context=merged_context,
    )
    overhead_min = float(profile["overhead_min"] or 0)
    min_transfer = int(profile["min_transfer"] or 0)

    pure_travel_minutes = (distance_km / speed_kmh) * 60 if speed_kmh > 0 else 0
    total_minutes = pure_travel_minutes + overhead_min

    return max(min_transfer, int(total_minutes))


# Оценивает время перемещения между двумя точками в минутах.
def estimate_transfer_time_minutes(
    from_place: Place,
    to_place: Place,
    merged_context: dict,
) -> int:
    distance_km = haversine_distance_km(
        from_place.lat,
        from_place.lng,
        to_place.lat,
        to_place.lng,
    )

    route_mode = merged_context.get("route_mode") or "walk"

    return _compute_transfer_minutes(
        distance_km=distance_km,
        route_mode=route_mode,
        merged_context=merged_context,
    )


# Оценивает переход от стартовой точки пользователя до первой точки маршрута.
# Это критично, чтобы time budget был честнее.
def estimate_start_to_first_place_transfer_minutes(
    start_context,
    first_place: Place,
    merged_context: dict,
) -> int:
    if start_context is None:
        return 0

    if getattr(start_context, "source", None) == "invalid":
        return 0

    start_lat = getattr(start_context, "lat", None)
    start_lng = getattr(start_context, "lng", None)

    if start_lat is None or start_lng is None:
        return 0

    distance_km = haversine_distance_km(
        start_lat,
        start_lng,
        first_place.lat,
        first_place.lng,
    )

    route_mode = merged_context.get("route_mode") or "walk"

    return _compute_transfer_minutes(
        distance_km=distance_km,
        route_mode=route_mode,
        merged_context=merged_context,
    )


# Оценивает время пребывания на точке в минутах.
# Если у точки задан average_visit_duration_minutes, берем его как источник правды.
def estimate_place_dwell_time_minutes(place: Place, merged_context: dict) -> int:
    if getattr(place, "average_visit_duration_minutes", None):
        base_minutes = place.average_visit_duration_minutes
    else:
        base_minutes = PLACE_DWELL_MINUTES.get(place.category, DEFAULT_DWELL_MINUTES)

    preferences = merged_context.get("preferences", {})
    interests: list[str] = preferences.get("interests", [])

    bonus_minutes = 0

    if place.category == "cafe":
        if "coffee" in interests:
            bonus_minutes += 5
        if "food" in interests:
            bonus_minutes += 10

    if place.category in {"walk", "park"} and ("walk" in interests or "quiet" in interests):
        bonus_minutes += 10

    return base_minutes + bonus_minutes