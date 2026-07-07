"""Explicit DB schema contracts for admin diagnostics (read-only checks)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SchemaContract:
    key: str
    tables: tuple[str, ...]
    columns: dict[str, tuple[str, ...]]


IMPORT_PLACES_COLUMNS: tuple[str, ...] = (
    "id",
    "city_id",
    "primary_destination_id",
    "destination_assignment_stale",
    "category_id",
    "slug",
    "title",
    "status",
    "internal_status",
    "lifecycle_status",
    "place_layer",
    "route_policy",
    "tourist_eligible",
    "transport_required",
    "lat",
    "lng",
    "image_url",
    "address",
    "short_description",
    "route_exclusion_reason",
    "quality_score",
    "photo_score",
    "is_spam_poi",
    "is_duplicate_suspected",
    "canonical_category",
    "is_published",
    "is_visible_in_catalog",
    "is_route_eligible",
    "publication_status",
    "updated_at",
)

SOURCE_OBSERVATIONS_COLUMNS: tuple[str, ...] = (
    "id",
    "import_batch_id",
    "city_id",
    "scope_id",
    "source_type",
    "source_external_id",
    "source_object_type",
    "source_url",
    "source_license",
    "attribution_text",
    "idempotency_key",
    "raw_name",
    "raw_category",
    "raw_lat",
    "raw_lng",
    "raw_payload",
    "payload_hash",
    "first_seen_at",
    "last_seen_at",
    "seen_in_batch_id",
    "canonical_place_id",
    "match_status",
    "normalization_status",
    "rejection_reason",
    "confidence",
    "created_at",
    "updated_at",
)

IMPORT_CRITICAL = SchemaContract(
    key="import_critical",
    tables=(
        "places",
        "cities",
        "city_import_scopes",
        "city_admin_import_jobs",
        "import_batches",
        "review_queue_items",
        "place_images",
        "place_field_provenance",
        "source_observations",
        "place_source_presence",
    ),
    columns={
        "places": IMPORT_PLACES_COLUMNS,
        "city_import_scopes": ("id", "city_id", "code", "enabled", "status", "bbox", "import_profile"),
        "city_admin_import_jobs": ("id", "city_id", "status", "source", "current_step", "step_details"),
        "import_batches": ("id", "scope_id", "status", "raw_count"),
        "review_queue_items": ("id", "place_id", "status", "job_id"),
        "place_images": ("id", "place_id", "image_url", "status", "source_type"),
        "place_field_provenance": ("id", "place_id", "field_name", "source", "confidence"),
        "source_observations": SOURCE_OBSERVATIONS_COLUMNS,
        "place_source_presence": ("id", "place_id", "source_external_id"),
    },
)

PHOTO_CRITICAL = SchemaContract(
    key="photo_critical",
    tables=("places", "place_images", "place_source_presence", "source_observations"),
    columns={
        "places": ("id", "city_id", "image_url", "status", "title", "lat", "lng", "photo_score"),
        "place_images": ("id", "place_id", "image_url", "status", "source_type", "is_primary"),
        "place_source_presence": ("id", "place_id", "source_external_id"),
        "source_observations": ("id", "canonical_place_id", "raw_payload"),
    },
)

ROUTE_CRITICAL = SchemaContract(
    key="route_critical",
    tables=("places", "categories"),
    columns={
        "places": (
            "id",
            "city_id",
            "place_layer",
            "route_policy",
            "tourist_eligible",
            "transport_required",
            "is_route_eligible",
            "canonical_category",
            "category_id",
            "quality_score",
            "publication_status",
            "is_published",
            "lat",
            "lng",
            "title",
        ),
        "categories": ("id", "code", "is_active"),
    },
)

SCHEMA_CONTRACTS: tuple[SchemaContract, ...] = (IMPORT_CRITICAL, PHOTO_CRITICAL, ROUTE_CRITICAL)
