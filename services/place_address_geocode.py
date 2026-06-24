"""Каскад reverse geocoding для обогащения адресов мест."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from core.config import settings
from services.local_persistent_cache import get_cached_json, set_cached_json, stable_cache_key

NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
GEOAPIFY_REVERSE_URL = "https://api.geoapify.com/v1/geocode/reverse"
DEFAULT_USER_AGENT = "CityGoAddressBackfill/1.0"
CACHE_NAMESPACE = "nominatim_reverse_v1"


@dataclass(frozen=True)
class ReverseGeocodeCandidate:
    address: str
    source: str
    confidence: float
    precision: str
    distance_meters: float | None = None
    locality: str | None = None
    raw_payload: dict[str, Any] | None = None


def geocoder_user_agent() -> str:
    value = str(settings.place_address_geocoder_user_agent or "").strip()
    if not value or "example.com" in value.casefold():
        return DEFAULT_USER_AGENT
    return value


def reverse_geocode_candidate(lat: float, lng: float, *, category: str | None = None) -> ReverseGeocodeCandidate | None:
    """Return the best legal, cacheable address candidate for the coordinates."""
    candidates: list[ReverseGeocodeCandidate] = []
    if str(settings.geoapify_api_key or "").strip():
        try:
            candidate = _geoapify_candidate(lat, lng, category=category)
            if candidate:
                candidates.append(candidate)
        except Exception:
            pass
    try:
        candidate = _nominatim_candidate(lat, lng, category=category)
        if candidate:
            candidates.append(candidate)
    except Exception:
        pass
    return max(candidates, key=lambda item: item.confidence, default=None)


def reverse_geocode(lat: float, lng: float) -> str | None:
    candidate = reverse_geocode_candidate(lat, lng)
    return candidate.address if candidate else None


def reverse_geocode_payload(lat: float, lng: float) -> dict[str, Any]:
    params_payload = {
        "format": "jsonv2",
        "lat": f"{lat:.7f}",
        "lon": f"{lng:.7f}",
        "addressdetails": "1",
        "namedetails": "1",
        "extratags": "1",
        "accept-language": "ru",
        "zoom": "18",
    }
    cache_key = stable_cache_key(CACHE_NAMESPACE, params_payload)
    found, cached = get_cached_json(cache_key)
    if found and isinstance(cached, dict):
        return cached
    request = urllib.request.Request(
        f"{NOMINATIM_REVERSE_URL}?{urllib.parse.urlencode(params_payload)}",
        headers={"User-Agent": geocoder_user_agent(), "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=settings.geocoding_timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        set_cached_json(cache_key, payload, tag="provider:nominatim")
        return payload
    return {}


def _geoapify_payload(lat: float, lng: float) -> dict[str, Any]:
    params_payload = {
        "lat": f"{lat:.7f}",
        "lon": f"{lng:.7f}",
        "lang": "ru",
        "format": "json",
        "apiKey": str(settings.geoapify_api_key).strip(),
    }
    cache_key = stable_cache_key("geoapify_reverse_v1", {key: value for key, value in params_payload.items() if key != "apiKey"})
    found, cached = get_cached_json(cache_key)
    if found and isinstance(cached, dict):
        return cached
    request = urllib.request.Request(
        f"{GEOAPIFY_REVERSE_URL}?{urllib.parse.urlencode(params_payload)}",
        headers={"User-Agent": geocoder_user_agent(), "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=settings.geocoding_timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        set_cached_json(cache_key, payload, tag="provider:geoapify")
        return payload
    return {}


def _geoapify_candidate(lat: float, lng: float, *, category: str | None) -> ReverseGeocodeCandidate | None:
    payload = _geoapify_payload(lat, lng)
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        return None
    props = results[0]
    road = _first(props, "street", "address_line1")
    house = _first(props, "housenumber")
    locality = _first(props, "suburb", "district", "city", "town", "village")
    city = _first(props, "city", "town", "village", "municipality")
    address, precision, confidence = _format_components(road, house, locality, city, category)
    if not address:
        return None
    rank = props.get("rank") if isinstance(props.get("rank"), dict) else {}
    confidence = min(0.98, max(confidence, float(rank.get("confidence") or 0)))
    distance = _float_or_none(props.get("distance"))
    if distance is not None and distance > 250:
        confidence = min(confidence, 0.45)
    return ReverseGeocodeCandidate(address, "geoapify_reverse", confidence, precision, distance, locality, payload)


def _nominatim_candidate(lat: float, lng: float, *, category: str | None) -> ReverseGeocodeCandidate | None:
    payload = reverse_geocode_payload(lat, lng)
    address_data = payload.get("address") if isinstance(payload.get("address"), dict) else {}
    road = _first(address_data, "road", "pedestrian", "footway", "path", "cycleway")
    house = _first(address_data, "house_number")
    locality = _first(address_data, "suburb", "neighbourhood", "quarter", "city_district")
    city = _first(address_data, "city", "town", "village", "municipality")
    address, precision, confidence = _format_components(road, house, locality, city, category)
    if not address:
        return None
    return ReverseGeocodeCandidate(address, "nominatim_reverse", confidence, precision, None, locality, payload)


def _format_components(
    road: str | None,
    house: str | None,
    locality: str | None,
    city: str | None,
    category: str | None,
) -> tuple[str | None, str, float]:
    location_category = str(category or "").casefold() in {"walk", "park", "beach", "outdoor", "viewpoint", "nature"}
    if road and house:
        parts = [f"{road} {house}", locality, city]
        return _join_unique(parts), "building", 0.95
    if road:
        prefix = "Рядом с " if location_category else ""
        parts = [f"{prefix}{road}", locality, city]
        return _join_unique(parts), "street", 0.82 if location_category else 0.72
    if location_category and (locality or city):
        return _join_unique([locality, city]), "locality", 0.58
    return None, "unknown", 0.0


def format_nominatim_address(payload: dict[str, Any]) -> str | None:
    address = payload.get("address") if isinstance(payload.get("address"), dict) else {}
    formatted, _, _ = _format_components(
        _first(address, "road", "pedestrian", "footway", "path", "cycleway"),
        _first(address, "house_number"),
        _first(address, "suburb", "neighbourhood", "quarter", "city_district"),
        _first(address, "city", "town", "village", "municipality"),
        None,
    )
    return formatted


def _join_unique(parts: list[str | None]) -> str | None:
    values: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value.casefold() not in {item.casefold() for item in values}:
            values.append(value)
    return ", ".join(values) if values else None


def _first(address: dict[str, Any], *keys: str) -> str | None:
    return next((str(address[key]).strip() for key in keys if str(address.get(key) or "").strip()), None)


def _float_or_none(value: object) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
