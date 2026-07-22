from __future__ import annotations

from typing import Any

from models.place import Place
from models.place_published_snapshot import PublishedPlaceSnapshot
from services.place_data_sanitizer import public_place_payload
from services.route_eligibility_policy import evaluate_place_route_eligibility


def build_snapshot_from_place(place: Place, *, snapshot_version: int = 1, locale: str = "default") -> PublishedPlaceSnapshot:
    """Build a Stage 1 read projection from the current legacy Place row."""

    destination_ids = [int(row.destination_id) for row in getattr(place, "destination_memberships", []) if getattr(row, "is_active", True)]
    tag_ids = [int(row.tag_id) for row in getattr(place, "place_tags", [])]
    if place.primary_destination_id and place.primary_destination_id not in destination_ids:
        destination_ids.append(int(place.primary_destination_id))
    route_payload = {
        key: getattr(place, key, None) for key in (
            "id", "city_id", "slug", "title", "short_description", "image_url", "address",
            "category_id", "category", "canonical_category", "lat", "lng", "opening_hours",
            "average_visit_duration_minutes", "price_level", "dog_friendly", "family_friendly",
            "indoor", "outdoor", "status", "is_active", "is_published", "is_route_eligible",
            "publication_status", "quality_score", "quality_tier", "verification_status",
            "is_visible_in_catalog", "internal_status", "lifecycle_status", "place_layer",
            "tourist_eligible", "transport_required", "route_policy", "is_spam_poi",
            "is_duplicate_suspected", "critical_field_expired",
        )
    }
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
        "category_id": place.category_id,
        "primary_destination_id": place.primary_destination_id,
        "destination_ids": destination_ids,
        "tag_ids": tag_ids,
        "route_payload": route_payload,
        "public_payload": public_place_payload(place, [place.image_url] if place.image_url else None),
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
        is_route_visible=bool(place.is_route_eligible and evaluate_place_route_eligibility(place, require_stored_flag=True).eligible),
        snapshot_payload=snapshot_payload,
        quality_payload=quality_payload,
        media_payload={"image_url": place.image_url},
        source_event_type="legacy_compatibility",
    )
