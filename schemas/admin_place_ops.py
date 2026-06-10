from datetime import datetime
from pydantic import BaseModel, Field


class AdminPlaceDetailRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    city_slug: str | None = None
    city_name: str | None = None
    category: str | None = None
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
    publication_status: str
    verification_status: str
    visible_to_users: bool
    route_enabled: bool
    route_exclusion_reason: str | None = None
    existence_confidence_level: str
    admin_comment: str | None = None
    created_at: datetime
    updated_at: datetime
    route_usage_count: int = 0
    route_usage_note: str | None = None
    audit_history: list[dict[str, object]] = []


class AdminPlaceCreateDraftRequest(BaseModel):
    city_id: int
    title: str = Field(min_length=1)
    category: str
    source: str = "admin_manual"
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    short_description: str | None = None
    tag_ids: list[int] = []
    route_enabled: bool = False
    admin_comment: str | None = None


class AdminPlaceDuplicateCheckRequest(BaseModel):
    city_id: int
    title: str
    lat: float | None = None
    lng: float | None = None
    address: str | None = None


class AdminPlaceUpdateRequest(BaseModel):
    title: str | None = None
    category: str | None = None
    address: str | None = None
    short_description: str | None = None
    publication_status: str | None = None
    visible_to_users: bool | None = None
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
