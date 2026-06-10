import pytest
from datetime import datetime

from services.itinerary_time_service import is_place_open_at_time


def build_opening_hours_all_day():
    return {
        "mon": {"open": "00:00", "close": "23:59"},
        "tue": {"open": "00:00", "close": "23:59"},
        "wed": {"open": "00:00", "close": "23:59"},
        "thu": {"open": "00:00", "close": "23:59"},
        "fri": {"open": "00:00", "close": "23:59"},
        "sat": {"open": "00:00", "close": "23:59"},
        "sun": {"open": "00:00", "close": "23:59"},
    }


def build_opening_hours_day_only():
    return {
        "mon": {"open": "09:00", "close": "18:00"},
        "tue": {"open": "09:00", "close": "18:00"},
        "wed": {"open": "09:00", "close": "18:00"},
        "thu": {"open": "09:00", "close": "18:00"},
        "fri": {"open": "09:00", "close": "18:00"},
        "sat": None,
        "sun": None,
    }


def test_place_open_all_day():
    opening_hours = build_opening_hours_all_day()
    visit_time = datetime(2026, 4, 6, 12, 0)  # понедельник 12:00

    assert is_place_open_at_time(opening_hours, visit_time) is True


def test_place_closed_at_night():
    opening_hours = build_opening_hours_day_only()
    visit_time = datetime(2026, 4, 6, 22, 0)  # понедельник 22:00

    assert is_place_open_at_time(opening_hours, visit_time) is False


def test_place_open_during_day():
    opening_hours = build_opening_hours_day_only()
    visit_time = datetime(2026, 4, 6, 10, 0)  # понедельник 10:00

    assert is_place_open_at_time(opening_hours, visit_time) is True


def test_place_closed_weekend():
    opening_hours = build_opening_hours_day_only()
    visit_time = datetime(2026, 4, 5, 12, 0)  # воскресенье

    assert is_place_open_at_time(opening_hours, visit_time) is False


def test_no_opening_hours_defined():
    opening_hours = None
    visit_time = datetime(2026, 4, 6, 12, 0)

    # MVP логика: если нет данных — считаем, что открыто (fail-open)
    assert is_place_open_at_time(opening_hours, visit_time) is True
