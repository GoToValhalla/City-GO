"""CSV column definitions and row building for Place Data Enrichment exports."""
from __future__ import annotations

import csv
import io
import json

from models.place import Place

# Fixed columns always present in every export
BASE_COLUMNS = [
    "id", "slug", "title", "category", "city_slug", "city_name",
    "lat", "lng", "current_address", "current_website", "current_phone",
    "current_opening_hours", "current_image_url", "current_short_description",
    "current_price_level", "current_dog_friendly", "current_family_friendly",
    "current_outdoor", "current_indoor", "source", "source_url", "confidence",
    "publication_status", "is_published", "is_visible_in_catalog",
    "is_route_eligible", "verification_status", "raw_osm_tags", "notes",
]

SUGGESTED_COLUMNS = [
    "suggested_address", "suggested_website", "suggested_phone",
    "suggested_opening_hours", "suggested_menu_url", "suggested_social_links",
    "suggested_image_url", "suggested_short_description", "suggested_price_level",
    "suggested_dog_friendly", "suggested_family_friendly",
    "suggested_outdoor", "suggested_indoor",
    "suggested_cuisine", "suggested_average_check",
    "suggested_source_url", "suggested_data_source", "suggested_confidence",
    "suggested_comment",
    # Food/cafe/bar
    "suggested_takeaway", "suggested_delivery", "suggested_reservation_url",
    # Museum/culture
    "suggested_ticket_url", "suggested_ticket_price", "suggested_exhibition_url",
    # Park/beach/walk
    "suggested_facilities", "suggested_seasonality", "suggested_accessibility",
]

ALL_COLUMNS = BASE_COLUMNS + SUGGESTED_COLUMNS


def _fmt_hours(val: object) -> str:
    if not val:
        return ""
    return json.dumps(val, ensure_ascii=False) if isinstance(val, dict) else str(val)


def _place_row(place: Place, city_slug: str, city_name: str) -> dict[str, object]:
    base: dict[str, object] = {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "category": place.category or "",
        "city_slug": city_slug,
        "city_name": city_name,
        "lat": place.lat or "",
        "lng": place.lng or "",
        "current_address": place.address or "",
        "current_website": "",
        "current_phone": "",
        "current_opening_hours": _fmt_hours(place.opening_hours),
        "current_image_url": place.image_url or "",
        "current_short_description": place.short_description or "",
        "current_price_level": place.price_level if place.price_level is not None else "",
        "current_dog_friendly": "1" if place.dog_friendly else "",
        "current_family_friendly": "1" if place.family_friendly else "",
        "current_outdoor": "1" if place.outdoor else "",
        "current_indoor": "1" if place.indoor else "",
        "source": place.source or "",
        "source_url": place.source_url or "",
        "confidence": place.confidence if place.confidence is not None else "",
        "publication_status": place.publication_status or "",
        "is_published": "1" if place.is_published else "0",
        "is_visible_in_catalog": "1" if place.is_visible_in_catalog else "0",
        "is_route_eligible": "1" if place.is_route_eligible else "0",
        "verification_status": place.verification_status or "",
        "raw_osm_tags": "",
        "notes": "",
    }
    suggested = {col: "" for col in SUGGESTED_COLUMNS}
    return {**base, **suggested}


def build_csv(places: list[Place], city_slug: str, city_name: str) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=ALL_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for place in places:
        writer.writerow(_place_row(place, city_slug, city_name))
    return buf.getvalue()
