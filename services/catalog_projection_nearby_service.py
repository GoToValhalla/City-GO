"""Projection-only nearby catalog reader."""

from sqlalchemy.orm import Session

from models.search_routing_stage5 import SearchPlaceDocument
from services.catalog_projection_read_service import assert_all_document_scopes
from services.nearby_service import haversine_distance


def nearby_catalog_places(
    db: Session, *, lat: float, lng: float, radius_km: float,
) -> list[dict[str, object]]:
    rows = db.query(SearchPlaceDocument).filter(
        SearchPlaceDocument.is_public.is_(True),
        SearchPlaceDocument.is_catalog_visible.is_(True),
        SearchPlaceDocument.freshness_status == "fresh",
    ).all()
    assert_all_document_scopes(db, rows)
    pairs = [
        (row, haversine_distance(lat, lng, row.public_payload["lat"], row.public_payload["lng"]))
        for row in rows
        if row.public_payload.get("lat") is not None and row.public_payload.get("lng") is not None
    ]
    return sorted(
        [_payload(row, distance) for row, distance in pairs if distance <= radius_km],
        key=lambda item: (item["distance_km"], item["id"]),
    )


def _payload(row: SearchPlaceDocument, distance: float) -> dict[str, object]:
    payload = row.public_payload
    return {
        "id": row.place_id, "slug": payload["slug"], "title": payload["title"],
        "city_id": row.city_id, "category_id": (row.tags_payload or {}).get("category_id"),
        "category": payload["category"], "address": payload.get("address"),
        "lat": payload["lat"], "lng": payload["lng"], "distance_km": round(distance, 3),
    }
