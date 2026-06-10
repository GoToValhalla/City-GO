"""Поиск места по названию/адресу для админки (forward geocode)."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

from sqlalchemy.orm import Session

from models.city import City
from services.admin_place_duplicate_service import find_similar_places
from services.place_address_geocode import geocoder_user_agent

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"


def lookup_place_candidates(
    db: Session,
    *,
    city_id: int,
    query: str,
    limit: int = 5,
) -> dict[str, object]:
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        raise ValueError("Город не найден")
    q = query.strip()
    if not q:
        raise ValueError("Укажите название или адрес")
    search_q = f"{q}, {city.name}, {city.country}"
    geo = _nominatim_search(search_q, limit=limit)
    dupes = find_similar_places(db, city_id=city_id, title=q, address=q, lat=None, lng=None)
    return {"query": q, "city_slug": city.slug, "candidates": geo, "similar_places": dupes}


def _nominatim_search(query: str, *, limit: int) -> list[dict[str, object]]:
    params = urllib.parse.urlencode({"format": "jsonv2", "q": query, "limit": str(limit), "accept-language": "ru"})
    req = urllib.request.Request(f"{NOMINATIM_SEARCH}?{params}", headers={"User-Agent": geocoder_user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        return [{"error": str(exc)}]
    if not isinstance(payload, list):
        return []
    return [
        {
            "title": row.get("name") or row.get("display_name"),
            "address": row.get("display_name"),
            "lat": float(row["lat"]) if row.get("lat") else None,
            "lng": float(row["lon"]) if row.get("lon") else None,
            "source": "nominatim",
            "osm_type": row.get("osm_type"),
            "osm_id": row.get("osm_id"),
        }
        for row in payload
        if isinstance(row, dict)
    ]
