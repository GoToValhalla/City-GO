"""
Route Navigation Service.

Чистые функции для построения навигационного payload точки маршрута.
Без обращений к БД. Используется в сериализаторах и маперах.
"""

from __future__ import annotations

from services.place_address_policy import MISSING_ADDRESS_DISPLAY, is_real_address, is_unclear_for_display
from services.route_geometry import URBAN_FACTOR, WALK_METERS_PER_MIN

_GOOGLE_URL = "https://www.google.com/maps/search/?api=1&query={lat},{lng}"
_YANDEX_URL = "https://yandex.com/maps/?pt={lng},{lat}&z=17&l=map"
_OSM_URL = "https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"


def navigation_payload(
    lat: float,
    lng: float,
    address: str | None,
    estimated_walk_minutes: int | None = None,
    category: str | None = None,
) -> dict[str, object]:
    """
    Строит навигационные поля для точки маршрута.

    Всегда возвращает navigation URLs если есть координаты.
    display_location — адрес или fallback с координатами.
    """
    has_addr = is_real_address(address) and not is_unclear_for_display(address, category)
    display_loc = address if has_addr else MISSING_ADDRESS_DISPLAY
    return {
        "display_location": display_loc,
        "has_address": has_addr,
        "navigation_url_google": _GOOGLE_URL.format(lat=lat, lng=lng),
        "navigation_url_yandex": _YANDEX_URL.format(lat=lat, lng=lng),
        "navigation_url_osm": _OSM_URL.format(lat=lat, lng=lng),
        "estimated_distance_meters": _walk_to_meters(estimated_walk_minutes),
    }


def map_link_for_coords(lat: float, lng: float, provider: str = "google") -> str:
    """Возвращает URL карты для переданных координат."""
    if provider == "yandex":
        return _YANDEX_URL.format(lat=lat, lng=lng)
    if provider == "osm":
        return _OSM_URL.format(lat=lat, lng=lng)
    return _GOOGLE_URL.format(lat=lat, lng=lng)


def display_location(lat: float, lng: float, address: str | None) -> str:
    """Адрес или fallback для отображения."""
    return address if is_real_address(address) else MISSING_ADDRESS_DISPLAY


def _walk_to_meters(walk_minutes: int | None) -> int | None:
    if walk_minutes is None:
        return None
    return int(walk_minutes * WALK_METERS_PER_MIN / URBAN_FACTOR)
