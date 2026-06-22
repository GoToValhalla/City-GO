"""Схемы Route Operations (eligibility, data quality, readiness)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EligibilityPlaceRow(BaseModel):
    place_id: int
    title: str
    slug: str
    category: str | None = None
    eligible: bool
    quality_score: int
    quality_bucket: str
    reasons: list[str] = Field(default_factory=list)
    primary_reason: str
    city_slug: str | None = None


class EligibilityListResponse(BaseModel):
    items: list[EligibilityPlaceRow]
    total: int
    limit: int
    offset: int


class RouteReadinessPlace(BaseModel):
    place_id: int
    title: str
    slug: str
    category: str | None = None
    blockers: list[str] = Field(default_factory=list)
    quality_score: int


class RouteReadinessDiagnosticsResponse(BaseModel):
    city_slug: str
    city_name: str
    places_total: int
    eligible_places: int
    published_places: int
    blockers_count_by_reason: dict[str, int]
    near_ready_places: list[RouteReadinessPlace]
    sample_blocked_places: list[RouteReadinessPlace]


class DataQualityIssue(BaseModel):
    code: str
    count: int
    places_link: str


class DataQualityAction(BaseModel):
    code: str
    severity: str
    title: str
    count: int
    recommended_action: str
    admin_link: str


class DataQualityReport(BaseModel):
    city_slug: str
    city_name: str
    places_total: int
    places_eligible: int
    places_not_eligible: int
    places_with_photo: int
    places_without_photo: int
    places_with_address: int
    places_without_address: int
    places_with_description: int
    places_without_description: int
    category_counts: dict[str, int]
    forbidden_category_counts: dict[str, int]
    suspicious_category_counts: dict[str, int]
    quality_buckets: dict[str, int]
    issues: list[DataQualityIssue]
    action_plan: list[DataQualityAction] = Field(default_factory=list)


class CityReadinessResponse(BaseModel):
    city_slug: str
    city_name: str
    readiness_score: int
    status: str
    components: dict[str, float | int]


class CityReadinessListResponse(BaseModel):
    items: list[CityReadinessResponse]
