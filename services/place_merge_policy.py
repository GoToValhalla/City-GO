from __future__ import annotations

from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

MIN_CONFIDENCE_GATE = 0.6
SERVICE_ONLY_STATUS = "service_only"

FIELD_ALIASES = {
    "name": "title",
    "description": "short_description",
    "latitude": "lat",
    "longitude": "lng",
    "operating_hours": "opening_hours",
    "visit_duration_minutes": "average_visit_duration_minutes",
}

ALLOWED_FIELDS = {
    "title", "slug", "short_description", "address", "category", "canonical_category",
    "opening_hours", "lat", "lng", "image_url", "average_visit_duration_minutes",
}

SERVICE_ONLY_CATEGORIES = set(HARD_EXCLUDED_CATEGORIES)


def canonical_field(field: str) -> str:
    return FIELD_ALIASES.get(field, field)


def normalize_changes(changes: dict[str, object]) -> dict[str, object]:
    return {canonical_field(key): value for key, value in changes.items() if canonical_field(key) in ALLOWED_FIELDS}


def is_service_only_category(category: object) -> bool:
    return str(category or "").strip().lower() in SERVICE_ONLY_CATEGORIES
