from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
from schemas.place import PlaceCreate, PlaceRead, PlaceUpdate
from schemas.route import RouteDetailRead, RouteRead

class AdminActionRequest(BaseModel):
    actor: str = "admin"
    reason: str | None = None

class AdminUnpublishRequest(AdminActionRequest):
    reason: str = Field(min_length=1)

class AdminPlaceListResponse(BaseModel):
    items: list[PlaceRead]
    total: int
    limit: int
    offset: int

class AdminPlaceCreate(PlaceCreate):
    is_published: bool = False
    is_visible_in_catalog: bool = False
    is_route_eligible: bool = False
    is_searchable: bool = False
    publication_status: str = "draft"

class AdminPlaceUpdate(PlaceUpdate):
    pass

class AdminDashboardResponse(BaseModel):
    cities_total: int
    cities_published: int
    places_total: int
    places_published: int
    places_hidden: int
    places_needs_recheck: int
    places_low_confidence: int
    places_without_photo: int
    pending_photos: int
    routes_total: int
    routes_active: int
    audit_events_total: int = 0

class AdminCityCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    country: str = "Россия"
    region: str | None = None
    timezone: str = "Europe/Kaliningrad"
    center_lat: float | None = None
    center_lng: float | None = None
    radius_km: float | None = Field(default=15, ge=1, le=200)
    actor: str = "admin"

class AdminCityRead(BaseModel):
    id: int
    slug: str
    name: str
    country: str
    region: str | None = None
    timezone: str
    center_lat: float | None = None
    center_lng: float | None = None
    launch_status: str
    is_active: bool
    places_total: int = 0
    places_published: int = 0
    pending_photos: int = 0
    can_publish: bool = False
    can_unpublish: bool = False
    model_config = ConfigDict(from_attributes=True)

class AdminCityListResponse(BaseModel):
    items: list[AdminCityRead]
    total: int
    limit: int
    offset: int

class AdminCityImportResponse(BaseModel):
    city_id: int
    city_slug: str
    city_name: str
    job_status: str
    message: str
    next_step: str

class AdminCityPublicationResponse(BaseModel):
    city_id: int
    city_slug: str
    city_name: str
    launch_status: str
    is_active: bool
    places_total: int
    places_published: int
    places_hidden: int
    message: str

class AdminImportJobRead(BaseModel):
    id: str
    city_id: int
    city_slug: str
    city_name: str
    status: str
    launch_status: str | None = None
    is_city_active: bool = False
    current_step: str = "queued"
    current_step_label: str = "В очереди"
    source: str
    places_total: int
    places_published: int
    places_unpublished: int
    pending_photos: int
    next_step: str
    job_id: int | None = None
    scopes_total: int = 0
    scopes_succeeded: int = 0
    places_found: int = 0
    places_saved: int = 0
    total_items: int = 0
    processed_items: int = 0
    successful_items: int = 0
    failed_items: int = 0
    retry_count: int = 0
    step_details: dict[str, Any] | None = None
    is_stalled: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_error: str | None = None
    can_run: bool = False
    can_retry: bool = False
    can_cancel: bool = False
    can_publish: bool = False
    can_unpublish: bool = False
    report_url: str | None = None
    logs_url: str | None = None


class AdminImportJobActionResponse(BaseModel):
    city_id: int
    status: str
    message: str

class AdminImportJobListResponse(BaseModel):
    items: list[AdminImportJobRead]
    total: int
    limit: int
    offset: int

class AdminPlaceImageCreateRequest(BaseModel):
    place_id: int
    image_url: str
    thumbnail_url: str | None = None
    source_type: str = "manual_upload"
    source_url: str | None = None
    attribution: str | None = None
    license: str | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    comment: str | None = None
    actor: str = "admin"

class AdminPlaceImageRead(BaseModel):
    id: int
    place_id: int
    image_url: str
    thumbnail_url: str | None = None
    source_type: str
    source_url: str | None = None
    attribution: str | None = None
    license: str | None = None
    confidence: float | None = None
    status: str
    is_primary: bool
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_comment: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AdminAuditLogRead(BaseModel):
    id: int
    actor: str
    action: str
    entity_type: str
    entity_id: str | None = None
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None
    reason: str | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AdminAuditLogResponse(BaseModel):
    items: list[AdminAuditLogRead]
    total: int
    limit: int
    offset: int

class AdminRouteListResponse(BaseModel):
    items: list[RouteRead]
    total: int
    limit: int
    offset: int

class AdminRouteCreateRequest(BaseModel):
    city_id: int
    slug: str
    title: str
    short_description: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    route_mode: str = "walk"
    is_active: bool = False
    actor: str = "admin"

class AdminRouteUpdateRequest(BaseModel):
    slug: str | None = None
    title: str | None = None
    short_description: str | None = None
    duration_minutes: int | None = None
    distance_km: float | None = None
    route_mode: str | None = None
    is_active: bool | None = None
    actor: str = "admin"

class AdminRoutePointInput(BaseModel):
    place_id: int
    position: int

class AdminRoutePointsUpdateRequest(BaseModel):
    points: list[AdminRoutePointInput]
    actor: str = "admin"
    reason: str | None = None

class AdminRouteActionResponse(BaseModel):
    route: RouteDetailRead
    message: str