"""Проверка дублей при создании места."""

from __future__ import annotations

import math

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.place import Place


def find_similar_places(
    db: Session,
    *,
    city_id: int,
    title: str,
    lat: float | None = None,
    lng: float | None = None,
    address: str | None = None,
    limit: int = 10,
) -> list[dict[str, object]]:
    like = f"%{title.strip()}%"
    clauses = [Place.title.ilike(like)]
    if address and address.strip():
        clauses.append(Place.address.ilike(f"%{address.strip()}%"))
    from sqlalchemy import or_
    candidates = db.query(Place).filter(Place.city_id == city_id, or_(*clauses)).limit(limit * 2).all()
    seen: set[int] = set()
    result: list[dict[str, object]] = []
    for place in candidates:
        if place.id in seen:
            continue
        seen.add(place.id)
        reason = _match_reason(place, title, lat, lng, address)
        if reason:
            result.append({
                "id": place.id, "title": place.title, "slug": place.slug,
                "address": place.address, "lat": place.lat, "lng": place.lng,
                "match_reason": reason,
            })
        if len(result) >= limit:
            break
    return result


def _match_reason(place: Place, title: str, lat: float | None, lng: float | None, address: str | None) -> str | None:
    if place.title.lower().strip() == title.lower().strip():
        return "same_title"
    if address and place.address and address.lower() in place.address.lower():
        return "same_address"
    if lat is not None and lng is not None and _dist_m(place.lat, place.lng, lat, lng) < 50:
        return "nearby_coords"
    if title.lower() in place.title.lower() or place.title.lower() in title.lower():
        return "similar_title"
    return None


def _dist_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    return math.sqrt((lat1 - lat2) ** 2 + (lng1 - lng2) ** 2) * 111_000
