from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AdminActionCard(BaseModel):
    code: str
    title: str
    count: int
    severity: str
    link_path: str
    hint: str | None = None


class AdminOverviewResponse(BaseModel):
    critical: list[AdminActionCard]
    data_quality: list[AdminActionCard]
    operations: list[AdminActionCard]
    recent_audit_count: int
    generated_at: datetime


class FeatureToggleRead(BaseModel):
    key: str
    label: str | None = None
    description: str | None = None
    scope: str
    scope_id: str | None = None
    value_bool: bool
    default: bool | None = None
    group: str | None = None
    updated_by: str | None = None
    updated_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


class FeatureToggleGroupRead(BaseModel):
    code: str
    label: str


class FeatureToggleListResponse(BaseModel):
    items: list[FeatureToggleRead]
    total: int


class FeatureToggleUpdateRequest(BaseModel):
    value_bool: bool
    reason: str | None = Field(default=None, max_length=1000)


class AdminVerificationSummary(BaseModel):
    queue_total: int
    needs_recheck: int
    unverified: int
    low_confidence: int
    verified_today: int


class AdminMetricsSummary(BaseModel):
    dau: int
    mau: int
    routes_built: int
    routes_failed: int
    avg_route_stops: float
    routes_today: int = 0
    routes_week: int = 0
    routes_failed_week: int = 0
    route_success_rate: float | None = None
    places_total: int = 0
    places_published: int = 0
    places_no_photo: int = 0
    places_no_address: int = 0
    places_no_description: int = 0
    imports_ok_week: int = 0
    imports_fail_week: int = 0
    enrichment_ok_week: int = 0
    ai_requests_week: int = 0
    data_collection_note: str
