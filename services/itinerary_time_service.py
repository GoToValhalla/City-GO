from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from models.city import City
from models.place import Place
from services.itinerary_time_estimator import (
    estimate_place_dwell_time_minutes,
    estimate_start_to_first_place_transfer_minutes,
    estimate_transfer_time_minutes,
    haversine_distance_km,
)


WEEKDAY_MAP = {
    0: "mon",
    1: "tue",
    2: "wed",
    3: "thu",
    4: "fri",
    5: "sat",
    6: "sun",
}


# Возвращает timezone города.
# Если timezone явно передан — используем его.
# Если у города timezone заполнен — используем его.
# Иначе уходим в безопасный fallback.
def resolve_timezone_name(
    timezone_name: str | None,
    city: City | None,
) -> str:
    if timezone_name:
        return timezone_name

    city_timezone = getattr(city, "timezone", None)
    if city_timezone:
        return city_timezone

    return "Europe/Moscow"


# Преобразует строку HH:MM в объект time.
# Если формат некорректный — возвращает None.
def parse_time_string(value: str | None) -> time | None:
    if not value:
        return None

    try:
        parsed = datetime.strptime(value, "%H:%M")
        return parsed.time()
    except Exception:
        return None


# Проверяет, работает ли место 24 часа.
# В рамках текущей модели считаем 24h кейсом:
# open == close (например 00:00 -> 00:00).
def is_twenty_four_hours(open_time: time, close_time: time) -> bool:
    return open_time == close_time


# Возвращает нормализованное окно работы на конкретную дату.
# Если close <= open, считаем, что окно переходит через полночь.
def build_open_window_for_date(
    base_date,
    open_time: time,
    close_time: time,
) -> tuple[datetime, datetime]:
    open_dt = datetime.combine(base_date, open_time)
    close_dt = datetime.combine(base_date, close_time)

    if is_twenty_four_hours(open_time, close_time):
        close_dt = open_dt + timedelta(days=1)
    elif close_dt <= open_dt:
        close_dt = close_dt + timedelta(days=1)

    return open_dt, close_dt


def align_window_timezone(
    open_dt: datetime,
    close_dt: datetime,
    dt: datetime,
) -> tuple[datetime, datetime]:
    if dt.tzinfo is None:
        return open_dt, close_dt

    return open_dt.replace(tzinfo=dt.tzinfo), close_dt.replace(tzinfo=dt.tzinfo)


# Возвращает список рабочих окон, которые могут покрывать конкретный визит.
# Берем:
# 1) окно текущего дня
# 2) окно предыдущего дня, если оно тянется через полночь
def resolve_open_windows_for_datetime(
    opening_hours: dict,
    dt: datetime,
) -> list[tuple[datetime, datetime]]:
    windows: list[tuple[datetime, datetime]] = []

    weekday_key = WEEKDAY_MAP.get(dt.weekday())
    if weekday_key:
        day_info = opening_hours.get(weekday_key)
        if day_info:
            open_time = parse_time_string(day_info.get("open"))
            close_time = parse_time_string(day_info.get("close"))

            if open_time is not None and close_time is not None:
                open_dt, close_dt = build_open_window_for_date(
                    base_date=dt.date(),
                    open_time=open_time,
                    close_time=close_time,
                )
                windows.append(align_window_timezone(open_dt, close_dt, dt))

    previous_dt = dt - timedelta(days=1)
    previous_weekday_key = WEEKDAY_MAP.get(previous_dt.weekday())
    if previous_weekday_key:
        previous_day_info = opening_hours.get(previous_weekday_key)
        if previous_day_info:
            open_time = parse_time_string(previous_day_info.get("open"))
            close_time = parse_time_string(previous_day_info.get("close"))

            if open_time is not None and close_time is not None:
                previous_window = build_open_window_for_date(
                    base_date=previous_dt.date(),
                    open_time=open_time,
                    close_time=close_time,
                )
                previous_window = align_window_timezone(*previous_window, dt)

                # Добавляем только если окно реально заходит в текущие сутки.
                day_start = datetime.combine(dt.date(), time(0, 0))
                if dt.tzinfo is not None:
                    day_start = day_start.replace(tzinfo=dt.tzinfo)

                if previous_window[1] > day_start:
                    windows.append(previous_window)

    return windows


# Проверяет, открыто ли место в конкретный момент времени.
# Возвращает:
# - True, если место открыто
# - False, если место закрыто
# - None, если данных нет или они сломаны
def is_place_open_at(place: Place, dt: datetime) -> bool | None:
    opening_hours = getattr(place, "opening_hours", None)
    if not opening_hours:
        return None

    windows = resolve_open_windows_for_datetime(
        opening_hours=opening_hours,
        dt=dt,
    )

    if not windows:
        return False

    for open_dt, close_dt in windows:
        if open_dt <= dt <= close_dt:
            return True

    return False


# Утилита для тестов и упрощенных проверок.
# Работает напрямую с opening_hours, без Place-модели.
# Возвращает:
# - True, если открыто
# - False, если закрыто
# - True, если opening_hours отсутствует (fail-open для тестовых/фильтрационных сценариев)
def is_place_open_at_time(
    opening_hours: dict | None,
    dt: datetime,
) -> bool:
    if not opening_hours:
        return True

    windows = resolve_open_windows_for_datetime(
        opening_hours=opening_hours,
        dt=dt,
    )

    if not windows:
        return False

    for open_dt, close_dt in windows:
        if open_dt <= dt <= close_dt:
            return True

    return False


# Проверяет, открыто ли место хотя бы в какой-то момент в течение дня.
# Это нужно для candidate retrieval:
# мы не должны выкидывать место только потому, что оно закрыто в момент старта,
# если оно откроется позже в рамках того же дня.
def is_place_closed_all_day(
    place: Place,
    dt: datetime,
) -> bool | None:
    if not place.opening_hours:
        return None

    weekday_key = WEEKDAY_MAP.get(dt.weekday())
    if not weekday_key:
        return None

    day_info = place.opening_hours.get(weekday_key)
    if not day_info:
        return True

    open_time = parse_time_string(day_info.get("open"))
    close_time = parse_time_string(day_info.get("close"))

    if open_time is None or close_time is None:
        return None

    return False


# Возвращает локальное время старта в таймзоне города.
# Если trip_start_datetime naive, считаем, что оно уже задано в локальном времени города.
def get_local_trip_start_datetime(
    trip_start_datetime: datetime | None,
    timezone_name: str,
) -> datetime:
    tz = ZoneInfo(timezone_name)

    if trip_start_datetime is None:
        return datetime.now(tz)

    if trip_start_datetime.tzinfo is None:
        return trip_start_datetime.replace(tzinfo=tz)

    return trip_start_datetime.astimezone(tz)


# Считает реальные arrival times по маршруту.
# Это базовый кирпич для второго time-aware прохода.
def compute_visit_offsets(
    places: list[Place],
    merged_context: dict,
    timezone_name: str,
    trip_start_datetime: datetime | None,
    start_context=None,
) -> list[dict]:
    if not places:
        return []

    current_time = get_local_trip_start_datetime(
        trip_start_datetime=trip_start_datetime,
        timezone_name=timezone_name,
    )

    offsets: list[dict] = []

    for index, place in enumerate(places):
        if index == 0:
            transfer_minutes = estimate_start_to_first_place_transfer_minutes(
                start_context=start_context,
                first_place=place,
                merged_context=merged_context,
            )
        else:
            transfer_minutes = estimate_transfer_time_minutes(
                from_place=places[index - 1],
                to_place=place,
                merged_context=merged_context,
            )

        arrival_time = current_time + timedelta(minutes=transfer_minutes)
        dwell_minutes = estimate_place_dwell_time_minutes(
            place=place,
            merged_context=merged_context,
        )
        departure_time = arrival_time + timedelta(minutes=dwell_minutes)

        offsets.append(
            {
                "place_id": place.id,
                "estimated_arrival": arrival_time,
                "estimated_departure": departure_time,
                "transfer_minutes": transfer_minutes,
                "dwell_minutes": dwell_minutes,
            }
        )

        current_time = departure_time

    return offsets


# Считает общую дистанцию маршрута в километрах.
# Учитывает дистанцию от стартовой точки до первой точки маршрута.
def estimate_total_route_distance_km(
    places: list[Place],
    start_context=None,
) -> float:
    if not places:
        return 0.0

    total_distance_km = 0.0

    if start_context is not None and getattr(start_context, "source", None) != "invalid":
        start_lat = getattr(start_context, "lat", None)
        start_lng = getattr(start_context, "lng", None)

        if start_lat is not None and start_lng is not None:
            total_distance_km += haversine_distance_km(
                start_lat,
                start_lng,
                places[0].lat,
                places[0].lng,
            )

    for index in range(len(places) - 1):
        total_distance_km += haversine_distance_km(
            places[index].lat,
            places[index].lng,
            places[index + 1].lat,
            places[index + 1].lng,
        )

    return round(total_distance_km, 2)


# Контекстная надбавка на маршрут.
def estimate_context_overhead_minutes(
    places: list[Place],
    merged_context: dict,
) -> int:
    overhead_minutes = 0

    if any(place.category == "cafe" for place in places):
        overhead_minutes += 5

    if merged_context.get("with_children"):
        overhead_minutes += 5

    if merged_context.get("with_dog"):
        overhead_minutes += 3

    route_mode = merged_context.get("route_mode") or "walk"
    if route_mode == "public_transport":
        overhead_minutes += 8
    elif route_mode == "car":
        overhead_minutes += 4
    elif route_mode == "bike":
        overhead_minutes += 3
    elif route_mode == "mixed":
        overhead_minutes += 5

    return overhead_minutes


# Буферная надбавка ко времени маршрута.
def estimate_buffer_time_minutes(
    base_minutes: int,
    merged_context: dict,
) -> int:
    buffer_ratio = 0.15

    if merged_context.get("time_mode") == "explicit_budget":
        buffer_ratio = 0.1

    if merged_context.get("with_children"):
        buffer_ratio += 0.05

    if merged_context.get("with_dog"):
        buffer_ratio += 0.03

    return int(base_minutes * buffer_ratio)


# Считает общую длительность маршрута в минутах.
# Учитывает:
# - переход от старта до первой точки
# - dwell time на каждой точке
# - переходы между точками
# - контекстный overhead
# - буфер
def estimate_total_route_time_minutes(
    places: list[Place],
    merged_context: dict,
    start_context=None,
) -> int:
    if not places:
        return 0

    total_minutes = 0

    total_minutes += estimate_start_to_first_place_transfer_minutes(
        start_context=start_context,
        first_place=places[0],
        merged_context=merged_context,
    )

    for place in places:
        total_minutes += estimate_place_dwell_time_minutes(
            place=place,
            merged_context=merged_context,
        )

    for index in range(len(places) - 1):
        total_minutes += estimate_transfer_time_minutes(
            from_place=places[index],
            to_place=places[index + 1],
            merged_context=merged_context,
        )

    total_minutes += estimate_context_overhead_minutes(
        places=places,
        merged_context=merged_context,
    )

    total_minutes += estimate_buffer_time_minutes(
        base_minutes=total_minutes,
        merged_context=merged_context,
    )

    return total_minutes


# Оценивает статусы открытия точек в рамках уже собранного маршрута.
# Для каждой точки возвращает:
# - place_id
# - estimated_arrival
# - estimated_departure
# - is_open
def estimate_route_opening_statuses(
    places: list[Place],
    merged_context: dict,
    trip_start_datetime: datetime | None,
    timezone_name: str,
    start_context=None,
) -> list[dict]:
    if not places:
        return []

    offsets = compute_visit_offsets(
        places=places,
        merged_context=merged_context,
        timezone_name=timezone_name,
        trip_start_datetime=trip_start_datetime,
        start_context=start_context,
    )

    results: list[dict] = []

    places_by_id = {place.id: place for place in places}

    for item in offsets:
        place = places_by_id[item["place_id"]]
        is_open = is_place_open_at(
            place=place,
            dt=item["estimated_arrival"],
        )

        results.append(
            {
                "place_id": place.id,
                "estimated_arrival": item["estimated_arrival"],
                "estimated_departure": item["estimated_departure"],
                "is_open": is_open,
            }
        )

    return results
