"""
Контракт HTTP для POST /recommendations/route (recommendation pipeline).
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecommendationRouteRequest(BaseModel):
    """Минимальный ввод для построения маршрута и стартовый контекст пользователя."""

    lat: float = Field(..., description="Широта старта")
    lng: float = Field(..., description="Долгота старта")
    start_address: str | None = Field(default=None, max_length=500)
    start_source: str | None = Field(default="manual", max_length=32)
    time_budget_minutes: int | None = Field(default=None, ge=15, le=1440)
    time_of_day: str | None = Field(default=None, description="morning/afternoon/evening/night")
    route_time_mode: str | None = Field(default="flexible", description="now/today_later/flexible")
    interests: list[str] = Field(default_factory=list)
    avoided_categories: list[str] = Field(default_factory=list)
    excluded_place_ids: list[str] = Field(default_factory=list)
    budget_level: int | None = Field(default=None, ge=0, le=3)
    pace_mode: str | None = None
    is_visiting: bool = False
    city_slug: str | None = Field(default=None, max_length=100)
    city_id: str | None = None
    visit_city_id: str | None = None
    visit_days: int | None = Field(default=None, ge=1, le=30)
    user_id: str | None = Field(default=None, min_length=1, max_length=100)


class RecommendationRoutePointResponse(BaseModel):
    """Одна точка маршрута в JSON-ответе."""

    model_config = ConfigDict(extra="ignore")

    place_id: str
    city_slug: str | None = None
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
    estimated_arrival_time: str | None = Field(default=None, description="ISO 8601 или null")
    estimated_departure_time: str | None = Field(default=None, description="ISO 8601 или null")
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


class RouteUserWarning(BaseModel):
    type: str
    severity: str
    user_message: str
    affected_place_ids: list[str] = Field(default_factory=list)
    action_hint: str | None = None


class RecommendationRouteResponse(BaseModel):
    """Полное тело ответа POST /recommendations/route."""

    model_config = ConfigDict(extra="allow")

    route_id: str
    status: str = "ready"
    partial_reason: str | None = None
    total_places: int
    total_minutes: int
    total_estimated_minutes: int
    estimated_distance: float
    estimated_end_time: str | None = Field(default=None, description="ISO 8601 или null")
    has_warnings: bool
    warning_count: int
    places_with_warnings: list[str]
    quality_score: float = Field(default=0.0, ge=0.0, le=1.0)
    quality_status: str | None = None
    quality_breakdown: dict[str, float] = Field(default_factory=dict)
    route_quality_status: str | None = None
    route_completeness: float = 0.0
    matched_interest_count: int = 0
    total_requested_interests: int = 0
    expansion_level: str = "none"
    expanded_category_count: int = 0
    neutral_added_count: int = 0
    fallback_level: str = "none"
    user_explanation: str | None = None
    total_walk_distance_meters: int = Field(default=0, ge=0)
    time_breakdown: dict[str, float] = Field(default_factory=dict)
    category_distribution: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    user_warnings: list[RouteUserWarning] = Field(default_factory=list)
    points: list[RecommendationRoutePointResponse]
    candidate_options: list[RecommendationRoutePointResponse] = Field(default_factory=list)
    debug_trace: list[dict[str, Any]] = Field(default_factory=list)
    explanation: dict[str, Any]
