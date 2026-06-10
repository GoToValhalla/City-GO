"""Mapping suggested_* CSV columns to Place model fields."""
from __future__ import annotations

IMPORTABLE: dict[str, str] = {
    "suggested_address": "address",
    "suggested_short_description": "short_description",
    "suggested_price_level": "price_level",
    "suggested_dog_friendly": "dog_friendly",
    "suggested_family_friendly": "family_friendly",
    "suggested_outdoor": "outdoor",
    "suggested_indoor": "indoor",
    "suggested_opening_hours": "opening_hours",
}

IMAGE_PIPELINE = frozenset({"suggested_image_url"})

UNSUPPORTED = frozenset({
    "suggested_website", "suggested_phone", "suggested_menu_url",
    "suggested_social_links", "suggested_cuisine", "suggested_average_check",
    "suggested_source_url", "suggested_data_source", "suggested_confidence",
    "suggested_comment", "suggested_takeaway", "suggested_delivery",
    "suggested_reservation_url", "suggested_ticket_url", "suggested_ticket_price",
    "suggested_exhibition_url", "suggested_facilities", "suggested_seasonality",
    "suggested_accessibility",
})
