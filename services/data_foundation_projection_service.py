from __future__ import annotations

from typing import Any

from models.place import Place
from models.place_published_snapshot import PublishedPlaceSnapshot


def build_snapshot_from_place(place: Place, *, snapshot_version: int = 1, locale: str = "default") -> PublishedPlaceSnapshot:
    """Build a Stage 1 read projection from the current legacy Place row."""

    snapshot_payload: dict[str, Any] = {
        "slug": place.slug,
        "title": place.title,
        "short_description": place.short_description,
        "image_url": place.image_url,
        "address": place.address,
        "lat": place.lat,
        "lng": place.lng,
        "category": place.category,
        "canonical_category": place.canonical_category,
        "opening_hours": place.opening_hours,
        "average_visit_duration_minutes": place.average_visit_duration_minutes,
    }

    quality_payload: dict[str, Any] = {
        "quality_score": place.quality_score,
        "quality_tier": place.quality_tier,
        "verification_status": place.verification_status,
    }

    return PublishedPlaceSnapshot(
        place_id=place.id,
        city_id=place.city_id,
        snapshot_version=snapshot_version,
        locale=locale,
        title=place.title,
        publication_status=place.publication_status,
        is_public=bool(place.is_published),
        is_catalog_visible=bool(place.is_visible_in_catalog),
        is_search_visible=bool(place.is_searchable),
        is_route_visible=bool(place.is_route_eligible),
        snapshot_payload=snapshot_payload,
        quality_payload=quality_payload,
        media_payload={"image_url": place.image_url},
        source_event_type="legacy_compatibility",
    )
