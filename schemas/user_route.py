from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CorrectionAction = Literal["remove_place", "shorten_route", "rebuild_from_here", "avoid_category", "extend_route"]
BuildMode = Literal["auto", "by_categories", "manual", "constructor"]
StartType = Literal["current_location", "place", "map_point", "address", "city_center"]
QualityStatus = Literal["good", "acceptable", "weak", "failed"]


class UserRouteStart(BaseModel):
    type: StartType = "city_center"
    lat: float | None = None
    lng: float | None = None
    place_id: str | None = None
    address: str | None = None


class UserRouteIntent(BaseModel):
    lat: float
    lng: float
    start_address: str | None = None
    start_source: str | None = None
    start: UserRouteStart | None = None
    build_mode: BuildMode = "auto"
    time_budget_minutes: int | None = Field(default=None, ge=15, le=1440)
    time_of_day: str | None = Field(default=None, description="morning/afternoon/evening/night")
    route_time_mode: str | None = Field(default="flexible", description="now/today_later/flexible")
    interests: list[str] = Field(default_factory=list)
    avoided_categories: list[str] = Field(default_factory=list)
    excluded_place_ids: list[str] = Field(default_factory=list)
    budget_level: int | None = Field(default=None, ge=0, le=3)
    pace_mode: str | None = None
    is_visiting: bool = False
    city_id: str | None = None
    visit_city_id: str | None = None
    visit_days: int | None = Field(default=None, ge=1, le=30)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)


class UserRoutePoint(BaseModel):
    place_id: str
    city_slug: str | None = None
    position: int
    title: str | None = None
    address: str | None = None
    image_url: str | None = None
    short_description: str | None = None
    source: str | None = None
    lat: float
    lng: float
    category: str
    visit_minutes: int
    estimated_walk_minutes: int | None = None
    estimated_arrival_time: str | None = None
    estimated_departure_time: str | None = None
    time_status: str | None = None
    time_warning: str | None = None
    scoring_breakdown: dict[str, float] = Field(default_factory=dict)
    # Navigation payload — вычисляется при сериализации
    display_location: str | None = None
    has_address: bool = False
    navigation_url_google: str | None = None
    navigation_url_yandex: str | None = None
    navigation_url_osm: str | None = None
    estimated_distance_meters: int | None = None

    model_config = ConfigDict(extra="ignore")


class RouteUserWarning(BaseModel):
    type: str
    severity: str
    user_message: str
    affected_place_ids: list[str] = Field(default_factory=list)
    action_hint: str | None = None


class UserRouteState(BaseModel):
    route_id: str
    revision: int = 1
    status: str = "ready"
    partial_reason: str | None = None
    context: UserRouteIntent
    total_places: int
    total_minutes: int
    total_estimated_minutes: int
    estimated_distance: float
    estimated_end_time: str | None = None
    has_warnings: bool
    warning_count: int
    places_with_warnings: list[str] = Field(default_factory=list)
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_status: QualityStatus = "weak"
    quality_breakdown: dict[str, object] = Field(default_factory=dict)
    total_walk_distance_meters: int = Field(default=0, ge=0)
    time_breakdown: dict[str, float] = Field(default_factory=dict)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    user_warnings: list[RouteUserWarning] = Field(default_factory=list)
    points: list[UserRoutePoint] = Field(default_factory=list)
    candidate_options: list[UserRoutePoint] = Field(default_factory=list)
    explanation: dict[str, object] = Field(default_factory=dict)
    debug_trace: list[dict[str, object]] = Field(default_factory=list)


class UserRouteBuildRequest(UserRouteIntent):
    pass


class UserRoutePreviewRequest(UserRouteIntent):
    pass


class UserRouteCorrectRequest(BaseModel):
    current_route: UserRouteState
    action: CorrectionAction
    target_place_id: str | None = None
    current_lat: float | None = None
    current_lng: float | None = None
    new_time_budget_minutes: int | None = Field(default=None, ge=15, le=1440)
    avoided_categories: list[str] = Field(default_factory=list)
    replacement_strategy: str | None = "same_category"
    user_message: str | None = None


class UserRouteUpdateRequest(BaseModel):
    current_route: UserRouteState
    ordered_place_ids: list[str] = Field(min_length=1)


class UserRouteReplacePlaceRequest(BaseModel):
    current_route: UserRouteState
    old_place_id: str
    new_place_id: str


class UserRouteAddPlaceRequest(BaseModel):
    current_route: UserRouteState
    place_id: str
    insert_after_place_id: str | None = None


class UserRouteAlternativePlace(BaseModel):
    place_id: str
    city_slug: str | None = None
    title: str
    address: str | None = None
    image_url: str | None = None
    category: str | None = None
    score: float = 0.0
    walk_minutes: int | None = None


class UserRouteAlternativesResponse(BaseModel):
    route_id: str
    place_id: str
    options: list[UserRouteAlternativePlace]


class UserRouteSlotRequest(BaseModel):
    slot_id: str
    category: str
    preferred_place_id: str | None = None


class UserRouteStructuredBuildRequest(UserRouteIntent):
    slots: list[UserRouteSlotRequest] = Field(min_length=1, max_length=8)


class UserRouteSlotOption(BaseModel):
    place_id: str
    title: str
    address: str | None = None
    image_url: str | None = None
    category: str
    score: float
    walk_minutes: int | None = None


class UserRouteSlotOptions(BaseModel):
    slot_id: str
    category: str
    options: list[UserRouteSlotOption]


class UserRouteStructuredBuildResponse(BaseModel):
    city_id: str | None = None
    slots: list[UserRouteSlotOptions]
