from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AdminPlaceDetailRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    city_slug: str | None = None
    city_name: str | None = None
    category: str | None = None
    canonical_category: str | None = None
    tags: list[dict[str, object]] = []
    address: str | None = None
    address_source: str | None = None
    address_confidence: float | None = None
    address_updated_at: datetime | None = None
    lat: float
    lng: float
    short_description: str | None = None
    image_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    website: str | None = None
    phone: str | None = None
    atmosphere: str | None = None
    inside: str | None = None
    best_for: str | None = None
    opening_hours: dict[str, Any] | None = None
    average_visit_duration_minutes: int | None = None
    price_level: int | None = None
    indoor: bool = False
    outdoor: bool = False
    dog_friendly: bool = False
    family_friendly: bool = False
    is_active: bool = True
    status: str = "active"
    lifecycle_status: str = "active"
    quality_tier: str = "silver"
    quality_score: int = 0
    completeness_score: int = 0
    photo_score: int = 0
    description_score: int = 0
    confidence_score: int = 0
    freshness_score: int = 0
    publication_status: str
    verification_status: str
    visible_to_users: bool
    searchable: bool = False
    route_enabled: bool
    route_exclusion_reason: str | None = None
    existence_confidence_level: str
    existence_confidence_score: int = 0
    admin_comment: str | None = None
    created_at: datetime
    updated_at: datetime
    route_usage_count: int = 0
    route_usage_note: str | None = None
    audit_history: list[dict[str, object]] = []


class AdminPlaceCreateDraftRequest(BaseModel):
    city_id: int
    title: str = Field(min_length=1, max_length=255)
    category: str
    source: str = "admin_manual"
    source_url: str | None = None
    address: str | None = None
    lat: float
    lng: float
    short_description: str | None = None
    image_url: str | None = None
    website: str | None = None
    phone: str | None = None
    atmosphere: str | None = None
    inside: str | None = None
    best_for: str | None = None
    opening_hours: dict[str, Any] | None = None
    average_visit_duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price_level: int | None = Field(default=None, ge=1, le=4)
    indoor: bool = False
    outdoor: bool = False
    dog_friendly: bool = False
    family_friendly: bool = False
    tag_ids: list[int] = []
    route_enabled: bool = False
    admin_comment: str | None = None

    @model_validator(mode="after")
    def validate_coordinates(self):
        if not (-90 <= self.lat <= 90 and -180 <= self.lng <= 180):
            raise ValueError("Координаты находятся вне допустимого диапазона")
        if abs(self.lat) < 0.000001 and abs(self.lng) < 0.000001:
            raise ValueError("Нельзя создать место с координатами 0,0")
        return self


class AdminPlaceDuplicateCheckRequest(BaseModel):
    city_id: int
    title: str
    lat: float | None = None
    lng: float | None = None
    address: str | None = None


class AdminPlaceUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    address: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    short_description: str | None = None
    image_url: str | None = None
    source: str | None = None
    source_url: str | None = None
    website: str | None = None
    phone: str | None = None
    atmosphere: str | None = None
    inside: str | None = None
    best_for: str | None = None
    opening_hours: dict[str, Any] | None = None
    average_visit_duration_minutes: int | None = Field(default=None, ge=1, le=1440)
    price_level: int | None = Field(default=None, ge=1, le=4)
    indoor: bool | None = None
    outdoor: bool | None = None
    dog_friendly: bool | None = None
    family_friendly: bool | None = None
    is_active: bool | None = None
    status: str | None = None
    publication_status: str | None = None
    verification_status: str | None = None
    visible_to_users: bool | None = None
    searchable: bool | None = None
    route_enabled: bool | None = None
    route_exclusion_reason: str | None = None
    tag_ids: list[int] | None = None
    admin_comment: str | None = None
    reason: str | None = None


class AdminBulkPreviewRequest(BaseModel):
    place_ids: list[int] = Field(min_length=1)
    action: str
    params: dict[str, object] = {}


class AdminBulkApplyRequest(AdminBulkPreviewRequest):
    confirm: bool = False


class AdminAddressRefreshRequest(BaseModel):
    city_slug: str | None = None
    place_ids: list[int] = []


class AdminCityToggleUpdateRequest(BaseModel):
    key: str
    value_bool: bool
    reason: str | None = None
