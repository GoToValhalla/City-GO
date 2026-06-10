from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TimeMode = Literal["explicit_budget", "open_duration"]
RouteMode = Literal["walk", "public_transport", "car", "bike", "mixed"]

StartSourceType = Literal[
    "current_location",
    "typed_address",
    "selected_map_point",
    "place_id",
    "stay_location",
    "arrival_point",
    "saved_base",
    "area_anchor",
    "city_fallback",
]

ResolvedStartSource = Literal[
    "place_id",
    "geo_device",
    "city_anchor",
    "legacy_geo",
    "invalid",
]

AccuracyTier = Literal["precise", "approximate", "anchor"]


class StartGeoInput(BaseModel):
    lat: float | None = None
    lng: float | None = None
    accuracy_m: int | None = Field(default=None, ge=0, le=50000)


class StartContextInput(BaseModel):
    geo: StartGeoInput | None = None
    address: str | None = None
    place_id: int | None = None
    city: str | None = None
    source_type: StartSourceType | None = None
    lat: float | None = None
    lng: float | None = None
    area: str | None = None


class ItineraryPointRead(BaseModel):
    place_id: int
    position: int
    place_slug: str | None = None
    place_title: str | None = None
    reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class StartContextRead(BaseModel):
    source: ResolvedStartSource
    accuracy_tier: AccuracyTier
    lat: float
    lng: float
    display_label: str
    raw_address: str | None = None
    warning_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CurrentRoutePointRead(BaseModel):
    place_id: int
    position: int
    place_slug: str | None = None
    place_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class CurrentRouteContextRead(BaseModel):
    city_slug: str
    route_mode: RouteMode = "walk"
    points: list[CurrentRoutePointRead] = Field(default_factory=list)
    completed_place_ids: list[int] = Field(default_factory=list)
    remaining_time_minutes: int | None = None
    return_to_start: bool = False
    budget_level: int | None = None


class ItineraryGenerateRequest(BaseModel):
    city_slug: str
    user_id: int | None = None
    query: str | None = None
    time_mode: TimeMode = "open_duration"
    time_budget_minutes: int | None = Field(default=None, ge=15, le=2880)
    trip_start_datetime: datetime | None = None
    route_mode: RouteMode | None = None
    trip_days: int | None = Field(default=1, ge=1, le=2)
    with_dog: bool | None = None
    with_children: bool | None = None
    indoor_only: bool | None = None
    outdoor_only: bool | None = None
    budget_level: int | None = Field(default=None, ge=1, le=5)
    return_to_start: bool = False
    max_places: int | None = Field(default=5, ge=1, le=20)
    start_context: StartContextInput | None = None


class ItineraryGenerateResponse(BaseModel):
    status: str = "ok"
    title: str
    summary: str
    time_mode: TimeMode
    requested_duration_minutes: int | None = None
    estimated_duration_minutes: int | None = None
    distance_km: float | None = None
    route_mode: RouteMode = "walk"
    duration_fit_score: float | None = None
    start_context: StartContextRead | None = None
    points: list[ItineraryPointRead] = Field(default_factory=list)
    current_route_context: CurrentRouteContextRead | None = None
    explanation: str | None = None