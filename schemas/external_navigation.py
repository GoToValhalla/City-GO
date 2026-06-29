from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExternalNavigationProvider = Literal["yandex_maps", "2gis"]
ExternalNavigationMode = Literal["destination", "segment", "full_route"]
ExternalNavigationTransport = Literal["pedestrian"]
ExternalNavigationPlatform = Literal["web", "ios", "android", "telegram_mini_app"]


class ExternalNavigationLink(BaseModel):
    provider: ExternalNavigationProvider
    mode: ExternalNavigationMode
    transport: ExternalNavigationTransport = "pedestrian"
    label: str
    app_url: str | None = None
    web_url: str
    is_primary: bool = False
    is_app_link: bool = False
    platforms: list[ExternalNavigationPlatform] = Field(default_factory=lambda: ["web", "ios", "android", "telegram_mini_app"])


class ExternalNavigationPointLinks(BaseModel):
    point_index: int
    place_id: str | None = None
    title: str | None = None
    lat: float
    lng: float
    links: list[ExternalNavigationLink] = Field(default_factory=list)


class ExternalNavigationSegment(BaseModel):
    from_index: int
    to_index: int
    from_place_id: str | None = None
    to_place_id: str | None = None
    from_title: str | None = None
    to_title: str | None = None
    distance_m: int
    walk_duration_min: int
    links: list[ExternalNavigationLink] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExternalNavigationFullRoute(BaseModel):
    available: bool = False
    recommended: bool = False
    reason: str | None = None
    links: list[ExternalNavigationLink] = Field(default_factory=list)


class ExternalNavigationBlock(BaseModel):
    mode: Literal["segment_first"] = "segment_first"
    providers: list[ExternalNavigationProvider] = Field(default_factory=lambda: ["yandex_maps", "2gis"])
    navigation_ready_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    destination_links: list[ExternalNavigationPointLinks] = Field(default_factory=list)
    segments: list[ExternalNavigationSegment] = Field(default_factory=list)
    full_route: ExternalNavigationFullRoute = Field(default_factory=ExternalNavigationFullRoute)
    warnings: list[str] = Field(default_factory=list)
    future_internal_map_contract: str = "ordered_waypoints_and_segments"


class ExternalNavigationEventRequest(BaseModel):
    event_type: Literal[
        "external_navigation_opened",
        "external_navigation_fallback_used",
        "external_navigation_returned",
        "waypoint_confirmed",
        "waypoint_skipped",
        "route_completed",
        "route_abandoned",
    ]
    provider: ExternalNavigationProvider | None = None
    mode: ExternalNavigationMode | None = None
    from_index: int | None = Field(default=None, ge=0)
    to_index: int | None = Field(default=None, ge=0)
    platform: str | None = Field(default=None, max_length=64)
    client: str | None = Field(default=None, max_length=64)
    city_slug: str | None = Field(default=None, max_length=100)
    user_id: str | None = Field(default=None, max_length=100)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExternalNavigationEventResponse(BaseModel):
    recorded: bool = True
