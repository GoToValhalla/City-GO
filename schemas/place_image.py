from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaceImageReviewAction(BaseModel):
    reviewer: str | None = None
    comment: str | None = None


class PendingPlaceImageRead(BaseModel):
    image_id: int
    place_id: int
    place_title: str
    place_slug: str
    city_slug: str | None
    place_address: str | None
    place_category: str | None
    place_lat: float
    place_lng: float
    image_url: str
    thumbnail_url: str | None
    source_type: str
    source_url: str | None
    attribution: str | None
    license: str | None
    confidence: float | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaceImageActionResult(BaseModel):
    image_id: int = Field(validation_alias="id")
    place_id: int
    status: str
    is_primary: bool
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_comment: str | None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PendingPlaceImagesResponse(BaseModel):
    items: list[PendingPlaceImageRead]
    total: int
    limit: int
    offset: int


class PlaceImageEnqueueSummary(BaseModel):
    city_slug: str
    scanned_places: int = 0
    candidates_found: int = 0
    created: int = 0
    skipped_duplicates: int = 0
    skipped_has_approved: int = 0
    skipped_ineligible: int = 0
    dry_run: bool = True
    preview: list[dict[str, object]] = Field(default_factory=list)


class PlaceImageBulkReviewAction(PlaceImageReviewAction):
    image_ids: list[int] = Field(min_length=1, max_length=100)


class PlaceImageBulkActionResult(BaseModel):
    items: list[PlaceImageActionResult]
    missing_ids: list[int] = Field(default_factory=list)
