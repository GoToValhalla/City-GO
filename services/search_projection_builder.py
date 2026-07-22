"""Pure mapping and validation for SearchPlaceDocument rebuilds."""

from schemas.public_place import PublicPlaceRead
from services.public_read_projection_service import build_search_document_from_snapshot


def document_payload(snapshot: object, *, locale: str) -> dict[str, object]:
    payload = snapshot.snapshot_payload or {}
    quality = snapshot.quality_payload or {}
    return build_search_document_from_snapshot(
        snapshot={
            "place_id": snapshot.place_id,
            "city_id": snapshot.city_id,
            "snapshot_version": snapshot.snapshot_version,
            "title": snapshot.title,
            "description": payload.get("short_description"),
            "category": payload.get("canonical_category") or payload.get("category"),
            "tags": payload.get("tags") or [],
            "tag_ids": payload.get("tag_ids") or [],
            "category_id": payload.get("category_id"),
            "destination_ids": payload.get("destination_ids") or [],
            "is_public": snapshot.is_public,
            "is_search_visible": snapshot.is_search_visible,
            "is_catalog_visible": snapshot.is_catalog_visible,
            "ranking_score": quality.get("quality_score", 0),
            "public_payload": payload.get("public_payload") or {},
        },
        locale=locale,
    )


def valid_public_payload(snapshot: object) -> bool:
    try:
        PublicPlaceRead(**dict((snapshot.snapshot_payload or {}).get("public_payload") or {}))
    except (TypeError, ValueError):
        return False
    return True
