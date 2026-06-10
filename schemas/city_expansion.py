from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CountryCreate(BaseModel):
    code: str
    name: str
    default_locale: str | None = None


class CountryRead(CountryCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RegionCreate(BaseModel):
    country_id: int
    code: str
    name: str
    type: str = "region"
    timezone: str | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    bbox: dict[str, object] | None = None


class RegionRead(RegionCreate):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CityCandidateCreate(BaseModel):
    country_id: int
    region_id: int | None = None
    name: str
    normalized_name: str
    slug: str
    type: str = "city"
    status: str = "candidate"
    center_lat: float | None = None
    center_lng: float | None = None
    bbox: dict[str, object] | None = None


class CityCandidateRead(CityCandidateCreate):
    id: int
    confidence: float | None = None
    city_potential_score: float | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ImportScopeCreate(BaseModel):
    city_id: int
    code: str
    name: str
    priority: int = 100
    status: str = "draft"
    enabled: bool = False
    import_profile: str = "tourist_core"
    coverage_targets: dict[str, object] | None = None
    refresh_interval_hours: int | None = None
    bbox: dict[str, object] | None = None


class ImportScopeRead(ImportScopeCreate):
    id: int
    last_imported_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ImportCoverageReport(BaseModel):
    city_slug: str
    scope_code: str | None = None
    import_state: str = "not_started"
    raw_seen_count: int = 0
    normalized_count: int = 0
    linked_to_places_count: int = 0
    published_count: int = 0
    needs_review_count: int = 0
    rejected_count: int = 0
    user_missing_reports_count: int = 0
    possible_removed_count: int = 0
    categories_distribution: dict[str, int] = Field(default_factory=dict)
    coverage_status: str = "not_started"
    blockers: list[str] = Field(default_factory=list)
