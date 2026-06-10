from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass

from core.config import settings


@dataclass(frozen=True)
class GeoPoint:
    """Результат геокодинга: координаты и нормализованный адрес, если провайдер его вернул."""

    lat: float
    lng: float
    formatted_address: str | None = None
    provider: str = "geoapify"


class GeocodingService:
    """Тонкий sync-клиент Geoapify для start_address в построении маршрутов."""

    def geocode(self, address: str, city_name: str | None = None) -> GeoPoint | None:
        query = self._build_query(address, city_name)
        if not query or not settings.geoapify_api_key:
            return None

        params = urllib.parse.urlencode(
            {
                "text": query,
                "lang": "ru",
                "limit": 1,
                "apiKey": settings.geoapify_api_key,
            }
        )
        url = f"https://api.geoapify.com/v1/geocode/search?{params}"
        request = urllib.request.Request(url, headers={"User-Agent": "CityGoGeocoder/1.0"})

        try:
            with urllib.request.urlopen(request, timeout=settings.geocoding_timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

        features = payload.get("features") if isinstance(payload, dict) else None
        if not isinstance(features, list) or not features:
            return None

        properties = features[0].get("properties") or {}
        lat = properties.get("lat")
        lon = properties.get("lon")
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            return None

        return GeoPoint(
            lat=float(lat),
            lng=float(lon),
            formatted_address=properties.get("formatted") if isinstance(properties.get("formatted"), str) else None,
        )

    def _build_query(self, address: str, city_name: str | None) -> str:
        cleaned = " ".join(str(address or "").split())
        city = " ".join(str(city_name or "").split())
        if not cleaned:
            return ""
        if city and city.casefold() not in cleaned.casefold():
            return f"{cleaned}, {city}"
        return cleaned
