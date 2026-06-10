from datetime import datetime

from models.place import Place
from services.itinerary_time_service import is_place_open_at_time


# Создает тестовое место.
def build_place(place_id: int, opening_hours: dict | None) -> Place:
    place = Place()
    place.id = place_id
    place.title = f"Place {place_id}"
    place.lat = 54.0
    place.lng = 20.0
    place.opening_hours = opening_hours
    place.is_active = True
    place.category = "cafe"
    return place


# Дневной график (закрывается вечером).
def build_day_opening_hours():
    return {
        "mon": {"open": "09:00", "close": "18:00"},
        "tue": {"open": "09:00", "close": "18:00"},
        "wed": {"open": "09:00", "close": "18:00"},
        "thu": {"open": "09:00", "close": "18:00"},
        "fri": {"open": "09:00", "close": "18:00"},
        "sat": None,
        "sun": None,
    }


# 24/7 график.
def build_24h_opening_hours():
    return {
        "mon": {"open": "00:00", "close": "23:59"},
        "tue": {"open": "00:00", "close": "23:59"},
        "wed": {"open": "00:00", "close": "23:59"},
        "thu": {"open": "00:00", "close": "23:59"},
        "fri": {"open": "00:00", "close": "23:59"},
        "sat": {"open": "00:00", "close": "23:59"},
        "sun": {"open": "00:00", "close": "23:59"},
    }


# Проверяет, что generate-логика исключает закрытые точки.
def test_generate_excludes_closed_places():
    closed_place = build_place(1, build_day_opening_hours())  # закрыт вечером
    open_place = build_place(2, build_24h_opening_hours())    # открыт

    visit_time = datetime(2026, 4, 6, 22, 0)  # вечер

    candidates = [closed_place, open_place]

    # Имитация candidate filtering (как в generate)
    filtered = [
        place for place in candidates
        if is_place_open_at_time(place.opening_hours, visit_time)
    ]

    filtered_ids = [p.id for p in filtered]

    assert 2 in filtered_ids
    assert 1 not in filtered_ids
