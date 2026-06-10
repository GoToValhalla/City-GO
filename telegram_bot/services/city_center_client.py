from __future__ import annotations

from typing import cast

import httpx

from telegram_bot.services.backend_request_log import (
    log_backend_error,
    log_backend_success,
    request_started,
)
from telegram_bot.services.city_matcher import match_city

CityPayload = dict[str, object]


async def fetch_city_center_by_slug(
    base_url: str,
    slug: str,
    operation: str = "cities.by_slug",
) -> CityPayload:
    started = request_started()
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(f"{base_url}/cities/by-slug/{slug}")
            response.raise_for_status()
        log_backend_success(operation, base_url, started, response.status_code)
        return _city_center(cast(CityPayload, response.json()), base_url)
    except Exception as exc:
        log_backend_error(operation, base_url, started, exc)
        return {"ok": False, "base_url": base_url, "error": str(exc)}


async def fetch_city_center_for_text(
    base_url: str,
    text: str,
) -> CityPayload:
    cities = await _fetch_cities(base_url)
    city = match_city(cities, text)
    if city is not None:
        return _city_center(city, base_url, matched=True)
    return {"ok": False, "matched": False, "base_url": base_url, "error": "city not matched"}


async def _fetch_cities(base_url: str) -> list[CityPayload]:
    started = request_started()
    try:
        async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
            response = await client.get(f"{base_url}/cities/")
            response.raise_for_status()
        log_backend_success("cities.list", base_url, started, response.status_code)
        data = response.json()
        return cast(list[CityPayload], data) if isinstance(data, list) else []
    except Exception as exc:
        log_backend_error("cities.list", base_url, started, exc)
        return []


def _city_center(
    city: CityPayload,
    base_url: str,
    matched: bool = False,
) -> CityPayload:
    lat = city.get("center_lat")
    lng = city.get("center_lng")
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return {"ok": False, "base_url": base_url, "error": "city center missing"}
    return {
        "ok": True,
        "lat": float(lat),
        "lng": float(lng),
        "slug": city.get("slug"),
        "name": city.get("name"),
        "launch_status": city.get("launch_status"),
        "matched": matched,
    }
