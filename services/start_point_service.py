from __future__ import annotations

from difflib import get_close_matches

from sqlalchemy.orm import Session

from models.city import City
from models.city_start_point import CityStartPoint
from models.place import Place
from schemas.start_point import ResolveStartRequest
from services.route_draft_rules import OUT_OF_CITY_MAX_METERS, normalize_text, warning
from services.route_geometry import distance_meters


def list_city_start_points(db: Session, city: City) -> list[dict[str, object]]:
    stored = (
        db.query(CityStartPoint)
        .filter(CityStartPoint.city_id == city.id, CityStartPoint.is_active.is_(True))
        .order_by(CityStartPoint.sort_order.asc(), CityStartPoint.id.asc())
        .all()
    )
    items = [_start_point_payload(item) for item in stored]
    if not items and city.center_lat is not None and city.center_lng is not None:
        items.append(_city_center_payload(city))
    return items


def resolve_start(db: Session, payload: ResolveStartRequest) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == payload.city_slug).first()
    if city is None or city.center_lat is None or city.center_lng is None:
        return None
    if payload.type == "geolocation" and payload.lat is not None and payload.lng is not None:
        return _resolve_geo(city, float(payload.lat), float(payload.lng))
    if payload.place_id is not None:
        place = db.query(Place).filter(Place.id == payload.place_id, Place.city_id == city.id).first()
        if place is not None:
            return _resolved("catalog_place", float(place.lat), float(place.lng), place.title, [], [])
    return _resolve_query(db, city, payload.query or "")


def _resolve_geo(city: City, lat: float, lng: float) -> dict[str, object]:
    meters = distance_meters(lat, lng, float(city.center_lat), float(city.center_lng))
    if meters <= OUT_OF_CITY_MAX_METERS:
        return _resolved("geolocation", lat, lng, "Моя геопозиция", [], [])
    return _resolved(
        "city_center",
        float(city.center_lat),
        float(city.center_lng),
        "Центр города",
        [warning("GEO_OUT_OF_CITY_FALLBACK", "Геопозиция далеко от города, старт перенесён в центр.")],
        [],
        out_of_city=True,
    )


def _resolve_query(db: Session, city: City, query: str) -> dict[str, object]:
    if not query:
        return _resolved("city_center", float(city.center_lat), float(city.center_lng), "Центр города", [], [])
    candidates = _query_candidates(db, city, query)
    if len(candidates) == 1:
        item = candidates[0]
        return _resolved(str(item["type"]), float(item["lat"]), float(item["lng"]), str(item["label_ru"]), [], [])
    if len(candidates) > 1:
        return _resolved("city_center", float(city.center_lat), float(city.center_lng), "Центр города", [], candidates)
    return _resolved(
        "city_center",
        float(city.center_lat),
        float(city.center_lng),
        "Центр города",
        [warning("ADDRESS_FALLBACK_CITY_CENTER", "Адрес не найден, используем центр города.")],
        [],
    )


def _query_candidates(db: Session, city: City, query: str) -> list[dict[str, object]]:
    normalized = normalize_text(query)
    start_points = list_city_start_points(db, city)
    places = db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).limit(100).all()
    place_items = [_place_payload(place) for place in places]
    pool = start_points + place_items
    exact = [item for item in pool if normalized in normalize_text(str(item.get("label_ru", "")))]
    if exact:
        return exact[:5]
    labels = {normalize_text(str(item.get("label_ru", ""))): item for item in pool}
    return [labels[key] for key in get_close_matches(normalized, list(labels), n=5, cutoff=0.55)]


def _resolved(kind: str, lat: float, lng: float, label: str, warnings: list[dict[str, str]], candidates: list[dict[str, object]], *, out_of_city: bool = False) -> dict[str, object]:
    return {"type": kind, "lat": lat, "lng": lng, "label": label, "out_of_city": out_of_city, "warnings": warnings, "candidates": candidates}

def _start_point_payload(item: CityStartPoint) -> dict[str, object]:
    return {"id": item.id, "label_ru": item.label_ru, "label_en": item.label_en, "lat": item.lat, "lng": item.lng, "type": item.type, "sort_order": item.sort_order, "place_id": item.place_id}


def _city_center_payload(city: City) -> dict[str, object]:
    return {"id": None, "label_ru": "Центр города", "label_en": "City center", "lat": city.center_lat, "lng": city.center_lng, "type": "city_center", "sort_order": 0, "place_id": None}


def _place_payload(place: Place) -> dict[str, object]:
    return {"id": None, "label_ru": place.title, "label_en": None, "lat": place.lat, "lng": place.lng, "type": "catalog_place", "sort_order": 100, "place_id": place.id}
