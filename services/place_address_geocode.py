"""Reverse geocoding для backfill адресов (Nominatim)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Any

from core.config import settings

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
DEFAULT_USER_AGENT = "CityGoAddressBackfill/1.0"


def geocoder_user_agent() -> str:
    value = str(settings.place_address_geocoder_user_agent or "").strip()
    if not value or "example.com" in value.casefold():
        return DEFAULT_USER_AGENT
    return value


def reverse_geocode_payload(lat: float, lng: float) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "format": "jsonv2",
        "lat": f"{lat:.7f}",
        "lon": f"{lng:.7f}",
        "addressdetails": "1",
        "accept-language": "ru",
        "zoom": "18",
    })
    request = urllib.request.Request(
        f"{NOMINATIM_REVERSE_URL}?{params}",
        headers={"User-Agent": geocoder_user_agent()},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def reverse_geocode(lat: float, lng: float) -> str | None:
    return format_nominatim_address(reverse_geocode_payload(lat, lng))


def format_nominatim_address(payload: dict[str, Any]) -> str | None:
    address = payload.get("address") or {}
    road = _first(address, "road", "pedestrian", "footway", "path", "cycleway")
    house = _first(address, "house_number")
    suburb = _first(address, "suburb", "neighbourhood", "quarter")
    city = _first(address, "city", "town", "village", "municipality")
    street_parts = [part for part in [road, house] if part]
    primary = " ".join(street_parts).strip()
    parts = [part for part in [primary, suburb, city] if part]
    if parts:
        return ", ".join(dict.fromkeys(parts))
    display_name = str(payload.get("display_name") or "").strip()
    return display_name or None


def _first(address: dict[str, Any], *keys: str) -> str | None:
    return next(
        (str(address[key]).strip() for key in keys if isinstance(address.get(key), str) and str(address[key]).strip()),
        None,
    )
