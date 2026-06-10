from datetime import datetime
import pytz

from services.itinerary_time_service import is_place_open_at_time


# Простой дневной график.
def build_opening_hours():
    return {
        "mon": {"open": "09:00", "close": "18:00"},
        "tue": {"open": "09:00", "close": "18:00"},
        "wed": {"open": "09:00", "close": "18:00"},
        "thu": {"open": "09:00", "close": "18:00"},
        "fri": {"open": "09:00", "close": "18:00"},
        "sat": None,
        "sun": None,
    }


# Проверяет, что время корректно интерпретируется в таймзоне города.
def test_timezone_local_time_correct():
    opening_hours = build_opening_hours()

    tz = pytz.timezone("Europe/Kaliningrad")

    # 10:00 по локальному времени города
    visit_time = tz.localize(datetime(2026, 4, 6, 10, 0))

    assert is_place_open_at_time(opening_hours, visit_time) is True


# Проверяет, что UTC время корректно смещается в локальное.
def test_timezone_utc_conversion():
    opening_hours = build_opening_hours()

    tz = pytz.timezone("Europe/Kaliningrad")

    # 07:00 UTC = 10:00 локального времени (UTC+3)
    visit_time_utc = datetime(2026, 4, 6, 7, 0, tzinfo=pytz.utc)

    visit_time_local = visit_time_utc.astimezone(tz)

    assert is_place_open_at_time(opening_hours, visit_time_local) is True


# Проверяет, что при неправильном времени (после закрытия) возвращается False.
def test_timezone_after_close():
    opening_hours = build_opening_hours()

    tz = pytz.timezone("Europe/Kaliningrad")

    visit_time = tz.localize(datetime(2026, 4, 6, 20, 0))  # 20:00

    assert is_place_open_at_time(opening_hours, visit_time) is False
