from datetime import datetime

from services.itinerary_time_service import is_place_open_at_time


# График с переходом через полночь, например для бара или позднего кафе.
def build_night_opening_hours():
    return {
        "mon": {"open": "18:00", "close": "02:00"},
        "tue": {"open": "18:00", "close": "02:00"},
        "wed": {"open": "18:00", "close": "02:00"},
        "thu": {"open": "18:00", "close": "02:00"},
        "fri": {"open": "18:00", "close": "03:00"},
        "sat": {"open": "18:00", "close": "03:00"},
        "sun": None,
    }


# Проверяет, что место считается открытым до полуночи.
def test_open_before_midnight():
    opening_hours = build_night_opening_hours()

    visit_time = datetime(2026, 4, 6, 23, 0)  # понедельник 23:00

    assert is_place_open_at_time(opening_hours, visit_time) is True


# Проверяет, что место считается открытым после полуночи,
# если интервал начался вечером предыдущего дня.
def test_open_after_midnight():
    opening_hours = build_night_opening_hours()

    visit_time = datetime(2026, 4, 7, 1, 0)  # вторник 01:00

    assert is_place_open_at_time(opening_hours, visit_time) is True


# Проверяет, что после завершения ночного интервала место уже закрыто.
def test_closed_after_night_shift():
    opening_hours = build_night_opening_hours()

    visit_time = datetime(2026, 4, 7, 4, 0)  # вторник 04:00

    assert is_place_open_at_time(opening_hours, visit_time) is False
