"""Telegram map URL builders and address display helpers."""

from __future__ import annotations

_PLACEHOLDER_ADDRESSES = frozenset({
    "адрес уточняется",
    "адрес не указан",
    "нет адреса",
    "unknown",
    "-",
})

_GOOGLE_URL = "https://www.google.com/maps/search/?api=1&query={lat},{lng}"
_YANDEX_URL = "https://yandex.com/maps/?pt={lng},{lat}&z=17&l=map"


def google_maps_link(lat: float, lng: float, label: str = "🗺 Google Maps") -> str:
    """HTML-ссылка на Google Maps для Telegram."""
    url = _GOOGLE_URL.format(lat=lat, lng=lng)
    return f'<a href="{url}">{label}</a>'


def yandex_maps_link(lat: float, lng: float, label: str = "🗺 Яндекс Карты") -> str:
    """HTML-ссылка на Яндекс Карты для Telegram."""
    url = _YANDEX_URL.format(lat=lat, lng=lng)
    return f'<a href="{url}">{label}</a>'


def point_location_text(address: str | None, lat: float, lng: float) -> str:
    """Адрес или координатный fallback для текстового отображения."""
    if address and address.casefold().strip() not in _PLACEHOLDER_ADDRESSES:
        return address
    return f"{lat:.4f}, {lng:.4f}"
