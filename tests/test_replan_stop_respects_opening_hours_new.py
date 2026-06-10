from datetime import datetime

from models.place import Place
from services.itinerary_time_service import is_place_open_at_time


# Создает тестовое место с нужной категорией и графиком работы.
def build_place(
    place_id: int,
    category: str,
    opening_hours: dict | None,
) -> Place:
    place = Place()
    place.id = place_id
    place.title = f"Place {place_id}"
    place.lat = 54.0
    place.lng = 20.0
    place.category = category
    place.opening_hours = opening_hours
    place.is_active = True
    place.price_level = 2
    place.city_id = 1
    return place


# Проверяет, что при выборе stop place закрытая точка не проходит,
# а выбирается только реально открытая.
def test_stop_not_selected_if_closed_new():
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

    # Закрытое вечером кафе.
    closed_cafe = build_place(1, "cafe", opening_day)

    # Кафе, которое открыто всегда.
    open_cafe = build_place(2, "cafe", opening_24h)

    # Проверяем вечернее время, когда обычное кафе уже закрыто.
    visit_time = datetime(2026, 4, 6, 22, 0)

    candidates = [closed_cafe, open_cafe]

    # Оставляем только реально открытые точки.
    valid_candidates = [
        place for place in candidates
        if is_place_open_at_time(place.opening_hours, visit_time)
    ]

    # Из оставшихся выбираем лучшего кандидата.
    selected = min(valid_candidates, key=lambda place: place.id)

    assert selected.id == 2