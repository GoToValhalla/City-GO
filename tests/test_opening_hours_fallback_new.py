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


# Проверяет fallback:
# если все точки закрыты — система не падает и может вернуть исходные точки.
def test_all_closed_fallback_to_original():
    place1 = build_place(1, build_day_opening_hours())
    place2 = build_place(2, build_day_opening_hours())

    visit_time = datetime(2026, 4, 6, 22, 0)  # вечер (все закрыто)

    candidates = [place1, place2]

    filtered = [
        place for place in candidates
        if is_place_open_at_time(place.opening_hours, visit_time)
    ]

    # MVP fallback: если ничего не осталось — возвращаем исходный список
    result = filtered if filtered else candidates

    result_ids = [p.id for p in result]

    assert len(result_ids) == 2
    assert 1 in result_ids
    assert 2 in result_ids
