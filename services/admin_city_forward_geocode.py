"""Forward geocoding города через Nominatim (admin city import)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from services.place_address_geocode import geocoder_user_agent

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class CityGeoResult:
    lat: float
    lng: float
    display_name: str | None = None


def geocode_city_name(*, name: str, country: str, region: str | None = None) -> CityGeoResult | None:
    parts = [name.strip(), region.strip() if region else "", country.strip()]
    query = ", ".join(part for part in parts if part)
    if not query:
        return None
    params = urllib.parse.urlencode({
        "format": "jsonv2",
        "q": query,
        "limit": "1",
        "accept-language": "ru",
    })
    request = urllib.request.Request(
        f"{NOMINATIM_SEARCH_URL}?{params}",
        headers={"User-Agent": geocoder_user_agent()},
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None
    if not isinstance(payload, list) or not payload:
        return None
    first = payload[0]
    lat = first.get("lat")
    lon = first.get("lon")
    if not isinstance(lat, str) or not isinstance(lon, str):
        return None
    return CityGeoResult(lat=float(lat), lng=float(lon), display_name=str(first.get("display_name") or "") or None)
