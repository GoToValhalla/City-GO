from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

SUPPORTED_MISSING_FIELDS = (
    "address", "website", "phone", "opening_hours", "photo",
    "description", "menu_url", "social_links", "price_level",
    "dog_friendly", "family_friendly", "outdoor", "indoor",
)

BATCH_STATUSES = ("exported", "enriched", "previewed", "imported", "failed")


class PlaceEnrichmentExportRequest(BaseModel):
    city_slug: str
    limit: int = Field(default=100, ge=1, le=500)
    only_published: bool = True
    only_unpublished: bool = False
    only_route_eligible: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    exclude_place_ids: list[int] = Field(default_factory=list)
    git_artifact: bool = True


class EnrichmentAIRequest(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    force: bool = False
    fields: list[str] = Field(default_factory=lambda: ["description"])
    model: str | None = None


class EnrichmentAIResult(BaseModel):
    batch_id: str
    status: str = "enriched"
    model: str
    rows_processed: int
    rows_updated: int
    errors: list[str]
    enriched_csv_path: str
    next_action: str = "preview_import"


class EnrichmentBatchMeta(BaseModel):
    batch_id: str
    status: str = "exported"
    city_slug: str
    limit: int
    missing_fields: list[str]
    only_published: bool
    only_route_eligible: bool
    export_csv_path: str
    enriched_csv_path: str
    import_preview_path: str
    import_result_path: str
    created_at: datetime
    total_exported: int
    by_city: dict[str, int]
    by_category: dict[str, int]
    missing_fields_breakdown: dict[str, int]
    next_action: str = "chatgpt_enrich"


class EnrichmentExportMeta(BaseModel):
    """Legacy + batch-compatible export response."""
    export_id: str
    batch_id: str | None = None
    status: str | None = None
    file_path: str
    export_csv_path: str | None = None
    enriched_csv_path: str | None = None
    city_slug: str | None = None
    total_exported: int
    by_city: dict[str, int]
    by_category: dict[str, int]
    missing_fields_breakdown: dict[str, int]
    created_at: datetime
    next_action: str | None = None


class EnrichmentBatchListResponse(BaseModel):
    items: list[EnrichmentBatchMeta]
    total: int


class EnrichmentExportListResponse(BaseModel):
    items: list[EnrichmentExportMeta]
    total: int


class ImportFieldUpdate(BaseModel):
    field: str
    old_value: Any
    new_value: Any
    source_column: str


class ImportRowPreview(BaseModel):
    place_id: int
    slug: str
    title: str
    updates: list[ImportFieldUpdate]
    skipped: list[str]


class ImportPreviewResult(BaseModel):
    batch_id: str
    mode: str = "preview"
    total_rows: int
    rows_with_changes: int
    changes: list[ImportRowPreview]
    skipped_rows: list[dict[str, Any]]
    unsupported_fields: dict[str, int]
    errors: list[str]


class ImportApplyResult(BaseModel):
    batch_id: str
    mode: str = "apply"
    rows_updated: int
    fields_updated: dict[str, int]
    skipped_unsupported_fields: dict[str, int]
    errors: list[str]