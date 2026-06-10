"""
tests/test_route_navigation_new.py

10 тестов для Route Address & Navigation Layer.
Все тесты юнит, без обращений к БД.
"""

from __future__ import annotations

import pytest

from services.place_address_policy import is_real_address
from services.route_navigation_service import (
    _walk_to_meters,
    display_location,
    map_link_for_coords,
    navigation_payload,
)
from telegram_bot.services.route_map_links import (
    google_maps_link,
    point_location_text,
    yandex_maps_link,
)
from telegram_bot.services.route_point_formatter import format_route_point


# ──────────────────────────────────────────────────────────────
# 1. display_location с адресом
# ──────────────────────────────────────────────────────────────
def test_display_location_returns_address_when_present():
    """Если адрес реальный — display_location = адрес."""
    payload = navigation_payload(
        lat=54.7104,
        lng=20.5122,
        address="ул. Пушкина, д. 10",
    )
    assert payload["display_location"] == "ул. Пушкина, д. 10"
    assert payload["has_address"] is True


# ──────────────────────────────────────────────────────────────
# 2. display_location без адреса → координаты
# ──────────────────────────────────────────────────────────────
def test_display_location_falls_back_to_coordinates_when_no_address():
    """Без адреса display_location содержит fallback-текст."""
    payload = navigation_payload(lat=54.7104, lng=20.5122, address=None)
    assert payload["display_location"] == "Адрес уточняется · открыть на карте"
    assert payload["has_address"] is False


# ──────────────────────────────────────────────────────────────
# 3. Placeholder-адрес трактуется как отсутствие адреса
# ──────────────────────────────────────────────────────────────
@pytest.mark.parametrize("placeholder", [
    "Адрес уточняется",
    "адрес не указан",
    "нет адреса",
    "unknown",
    "-",
])
def test_placeholder_address_treated_as_missing(placeholder: str):
    """Плейсхолдерный адрес → has_address=False, fallback-текст."""
    payload = navigation_payload(lat=54.0, lng=20.0, address=placeholder)
    assert payload["has_address"] is False
    assert payload["display_location"] == "Адрес уточняется · открыть на карте"


# ──────────────────────────────────────────────────────────────
# 4. Navigation URLs всегда присутствуют при наличии координат
# ──────────────────────────────────────────────────────────────
def test_navigation_urls_always_present_with_coordinates():
    """При наличии lat/lng все три navigation URL непусты и указывают на нужные сервисы."""
    payload = navigation_payload(lat=54.7104, lng=20.5122, address=None)
    assert payload["navigation_url_google"].startswith("https://www.google.com/maps/search/")
    assert payload["navigation_url_yandex"].startswith("https://yandex.com/maps/")
    assert payload["navigation_url_osm"].startswith("https://www.openstreetmap.org/")


# ──────────────────────────────────────────────────────────────
# 5. Google Maps URL содержит правильные координаты
# ──────────────────────────────────────────────────────────────
def test_google_maps_url_contains_correct_coords():
    payload = navigation_payload(lat=54.7104, lng=20.5122, address=None)
    assert "54.7104" in payload["navigation_url_google"]
    assert "20.5122" in payload["navigation_url_google"]
    assert "api=1" in payload["navigation_url_google"]


# ──────────────────────────────────────────────────────────────
# 6. estimated_distance_meters вычисляется из walk_minutes
# ──────────────────────────────────────────────────────────────
def test_estimated_distance_meters_computed_from_walk_minutes():
    """10 мин пешком → ~600 м (10 * 75 / 1.25 = 600)."""
    payload = navigation_payload(lat=54.0, lng=20.0, address=None, estimated_walk_minutes=10)
    assert payload["estimated_distance_meters"] == 600


def test_estimated_distance_meters_none_when_no_walk_minutes():
    payload = navigation_payload(lat=54.0, lng=20.0, address=None, estimated_walk_minutes=None)
    assert payload["estimated_distance_meters"] is None


# ──────────────────────────────────────────────────────────────
# 7. Telegram: point_location_text — address или coordinates
# ──────────────────────────────────────────────────────────────
def test_telegram_location_text_returns_address():
    result = point_location_text("ул. Ленина, 5", 54.0, 20.0)
    assert result == "ул. Ленина, 5"


def test_telegram_location_text_falls_back_to_coords():
    result = point_location_text(None, 54.7104, 20.5122)
    assert "54.7104" in result
    assert "20.5122" in result


# ──────────────────────────────────────────────────────────────
# 8. Telegram: google_maps_link содержит URL
# ──────────────────────────────────────────────────────────────
def test_telegram_google_maps_link_contains_url():
    link = google_maps_link(54.7104, 20.5122)
    assert "https://www.google.com/maps/search/" in link
    assert "<a href=" in link


# ──────────────────────────────────────────────────────────────
# 9. Telegram: format_route_point содержит map link
# ──────────────────────────────────────────────────────────────
def test_telegram_route_point_contains_map_link():
    """Отформатированная точка маршрута содержит HTML-ссылку на карту."""
    point = {
        "place_id": "42",
        "lat": 54.7104,
        "lng": 20.5122,
        "address": "ул. Пушкина, 10",
        "visit_minutes": 30,
        "estimated_walk_minutes": 5,
    }
    text = format_route_point(1, point, {"42": "Пушкинский парк"})
    assert "google.com/maps" in text
    assert "Пушкинский парк" in text
    assert "ул. Пушкина" in text


# ──────────────────────────────────────────────────────────────
# 10. Backfill: _needs_address не перетирает реальный адрес
# ──────────────────────────────────────────────────────────────
def test_address_backfill_does_not_overwrite_real_address():
    """
    Скрипт backfill проверяет _needs_address перед обновлением.
    Место с реальным адресом не должно попасть в список для обогащения.
    """
    from services.place_address_policy import needs_backfill

    assert needs_backfill("ул. Ленина, 1, Зеленоградск") is False
    assert needs_backfill(None) is True
    assert needs_backfill("нет адреса") is True
