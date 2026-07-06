"""Public and admin schemas for Destination foundation v1."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DestinationCenter(BaseModel):
    lat: float | None = None
    lng: float | None = None


class DestinationListItem(BaseModel):
    id: int
    slug: str
    title: str
    destination_type: str
    parent_id: int | None = None
    center: DestinationCenter
    readiness_score: int = 0
    has_children: bool = False
    places_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DestinationScopeSummary(BaseModel):
    id: int
    code: str
    name: str
    scope_type: str
    import_strategy: str = "single_bbox"
    import_profile: str = "tourist_core"
    bbox: dict[str, object] | None = None
    polygon: dict[str, object] | None = None
    priority: int = 0
    status: str = "draft"
    enabled: bool
    is_walkable_cluster: bool = False

    model_config = ConfigDict(from_attributes=True)


class DestinationDetail(DestinationListItem):
    launch_status: str
    is_published: bool
    sub_destinations: list[DestinationListItem] = Field(default_factory=list)
    scopes: list[DestinationScopeSummary] = Field(default_factory=list)


class DestinationListResponse(BaseModel):
    items: list[DestinationListItem]
    total: int


class AdminDestinationCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=1, max_length=255)
    destination_type: str = "region"
    parent_id: int | None = None
    legacy_city_id: int | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    bbox: dict[str, object] | None = None
    launch_status: str = "draft"
    is_published: bool = False


class AdminDestinationUpdate(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=120)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    destination_type: str | None = None
    parent_id: int | None = None
    legacy_city_id: int | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    bbox: dict[str, object] | None = None
    launch_status: str | None = None
    is_published: bool | None = None
    is_active: bool | None = None


class AdminDestinationScopeCreate(BaseModel):
    code: str
    name: str
    scope_type: str = "catalog"
    import_strategy: str = "single_bbox"
    bbox: dict[str, object] | None = None
    polygon: dict[str, object] | None = None
    import_profile: str = "tourist_core"
    is_walkable_cluster: bool = False
    priority: int = 0
    enabled: bool = True


class AdminDestinationScopeUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    scope_type: str | None = None
    import_strategy: str | None = None
    bbox: dict[str, object] | None = None
    polygon: dict[str, object] | None = None
    import_profile: str | None = None
    is_walkable_cluster: bool | None = None
    priority: int | None = None
    enabled: bool | None = None


class AdminAssignPlaceRequest(BaseModel):
    place_id: int
    is_primary: bool = False


class AdminHidePlaceRequest(BaseModel):
    place_id: int


class DestinationMembershipRead(BaseModel):
    id: int
    place_id: int
    destination_id: int
    assignment_type: str
    is_primary: bool
    confidence: float
    is_hidden: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
