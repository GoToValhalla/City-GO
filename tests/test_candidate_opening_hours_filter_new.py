from datetime import datetime

from models.place import Place
from services.itinerary_time_service import is_place_open_at_time


def build_place(place_id: int, opening_hours: dict | None) -> Place:
    place = Place()
    place.id = place_id
    place.title = f"Place {place_id}"
    place.lat = 54.0
    place.lng = 20.0
    place.opening_hours = opening_hours
    return place


def test_filter_only_open_places():
    opening_day = {
        "mon": {"open": "09:00", "close": "18:00"},
        "tue": {"open": "09:00", "close": "18:00"},
        "wed": {"open": "09:00", "close": "18:00"},
        "thu": {"open": "09:00", "close": "18:00"},
        "fri": {"open": "09:00", "close": "18:00"},
        "sat": None,
        "sun": None,
    }

    opening_24h = {
        "mon": {"open": "00:00", "close": "23:59"},
        "tue": {"open": "00:00", "close": "23:59"},
        "wed": {"open": "00:00", "close": "23:59"},
        "thu": {"open": "00:00", "close": "23:59"},
        "fri": {"open": "00:00", "close": "23:59"},
        "sat": {"open": "00:00", "close": "23:59"},
        "sun": {"open": "00:00", "close": "23:59"},
    }

    places = [
        build_place(1, opening_day),   # закрыт вечером
        build_place(2, opening_24h),   # всегда открыт
        build_place(3, None),          # нет данных → считаем открытым
    ]

    visit_time = datetime(2026, 4, 6, 22, 0)  # понедельник 22:00

    open_places = [
        place for place in places
        if is_place_open_at_time(place.opening_hours, visit_time)
    ]

    open_ids = [p.id for p in open_places]

    assert 2 in open_ids  # 24h
    assert 3 in open_ids  # unknown → allowed
    assert 1 not in open_ids  # закрыт


def test_all_closed_returns_empty():
    opening_day = {
        "mon": {"open": "09:00", "close": "18:00"},
        "tue": {"open": "09:00", "close": "18:00"},
        "wed": {"open": "09:00", "close": "18:00"},
        "thu": {"open": "09:00", "close": "18:00"},
        "fri": {"open": "09:00", "close": "18:00"},
        "sat": None,
        "sun": None,
    }

    places = [
        build_place(1, opening_day),
        build_place(2, opening_day),
    ]

    visit_time = datetime(2026, 4, 6, 22, 0)

    open_places = [
        place for place in places
        if is_place_open_at_time(place.opening_hours, visit_time)
    ]

    assert len(open_places) == 0
