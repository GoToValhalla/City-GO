from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class PlaceBase(BaseModel):
    city_id: int = 1
    category_id: int | None = None
    slug: str
    title: str
    short_description: str | None = None
    image_url: str | None = None
    image_id: int | None = None
    image_source_type: str | None = None
    image_attribution: str | None = None
    image_license: str | None = None
    image_confidence: float | None = None
    image_status: str | None = None
    image_reviewed_at: datetime | None = None
    opening_hours: dict[str, Any] | None = None
    average_visit_duration_minutes: int | None = None
    category: str | None = None
    address: str | None = None
    source: str | None = None
    source_url: str | None = None
    confidence: float | None = None
    last_verified_at: datetime | None = None
    status: str = "active"
    existence_confidence_score: int = 0
    existence_confidence_level: str = "unknown"
    verification_status: str = "unverified"
    verification_source: str | None = None
    verification_method: str | None = None
    verified_at: datetime | None = None
    verified_by: str | None = None
    needs_recheck_at: datetime | None = None
    verification_comment: str | None = None
    is_published: bool = False
    is_visible_in_catalog: bool = False
    is_route_eligible: bool = False
    is_searchable: bool = False
    publication_status: str = "draft"
    publication_comment: str | None = None
    published_at: datetime | None = None
    unpublished_at: datetime | None = None
    lat: float
    lng: float
    price_level: int | None = None
    dog_friendly: bool = False
    family_friendly: bool = False
    indoor: bool = False
    outdoor: bool = False
    is_active: bool = True


class PlaceCreate(PlaceBase):
    pass


class PlaceUpdate(PlaceBase):
    pass


class PlaceRead(PlaceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)