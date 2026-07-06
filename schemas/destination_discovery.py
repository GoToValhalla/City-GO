"""Schemas for admin region-first destination discovery."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DiscoverySeverity = Literal["info", "warning", "critical"]
DiscoveryTier = Literal["top", "high", "medium", "low", "unknown"]
JobStatus = Literal["pending", "running", "completed", "failed"]


class GeoPoint(BaseModel):
    lat: float
    lon: float


class GeoBbox(BaseModel):
    south: float
    west: float
    north: float
    east: float


class DiscoveryWarning(BaseModel):
    code: str
    severity: DiscoverySeverity
    message: str
    details: dict[str, object] | None = None


class ConfidenceScore(BaseModel):
    overall: float | None = None
    tourist_potential: float | None = None
    data_availability: float | None = None
    name_consistency: float | None = None
    existing_signal: float | None = None
    poi_signal: float | None = None
    wiki_signal: float | None = None
    reasons: list[str] = Field(default_factory=list)


class ExistingDestinationMatch(BaseModel):
    destination_id: int
    slug: str
    name: str
    match_type: str
    confidence: float | None = None


class ScopeOverlap(BaseModel):
    destination_slug: str
    scope_code: str
    scope_name: str
    overlap_type: str
    message: str


class RecommendedScope(BaseModel):
    code: str
    name: str
    scope_type: str = "catalog"
    import_profile: str = "tourist_core"
    bbox: GeoBbox | None = None
    center: GeoPoint | None = None
    radius_meters: int | None = None
    priority: int = 100
    reason: str
    warnings: list[DiscoveryWarning] = Field(default_factory=list)
    confidence: float | None = None


class RegionCandidate(BaseModel):
    id: str
    provider: str
    name: str
    local_name: str | None = None
    english_name: str | None = None
    country: str | None = None
    admin_level: int | None = None
    type: str
    center: GeoPoint
    bbox: GeoBbox | None = None
    importance_score: float | None = None
    matched_query: str
    warnings: list[DiscoveryWarning] = Field(default_factory=list)


class RegionSearchResponse(BaseModel):
    items: list[RegionCandidate]


class DiscoveryOptions(BaseModel):
    include_existing_destinations: bool = True
    include_towns: bool = True
    include_villages: bool = False
    include_border_candidates: bool = True
    include_poi_signals: bool = True
    max_candidates: int = Field(default=100, ge=1, le=500)


class DiscoverRegionRequest(BaseModel):
    provider: str = "auto"
    options: DiscoveryOptions = Field(default_factory=DiscoveryOptions)


class DestinationDiscoveryCandidate(BaseModel):
    id: str
    external_id: str
    provider: str
    name: str
    native_name: str | None = None
    english_name: str | None = None
    type: str
    parent_region: str | None = None
    center: GeoPoint | None = None
    bbox: GeoBbox | None = None
    population: int | None = None
    confidence: ConfidenceScore
    ranking_score: float
    tier: DiscoveryTier
    reasons: list[str] = Field(default_factory=list)
    warnings: list[DiscoveryWarning] = Field(default_factory=list)
    existing_match: ExistingDestinationMatch | None = None
    scope_overlaps: list[ScopeOverlap] = Field(default_factory=list)
    recommended_scopes: list[RecommendedScope] = Field(default_factory=list)
    created_destination_slug: str | None = None


class RegionDiscoveryJob(BaseModel):
    id: str
    status: JobStatus
    progress_percent: int = 0
    estimated_seconds: int | None = None
    error: str | None = None


class TierSummary(BaseModel):
    top: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0


class RegionDiscoveryPreview(BaseModel):
    region: RegionCandidate
    total_candidates: int
    tiers: TierSummary
    warnings: list[DiscoveryWarning] = Field(default_factory=list)
    candidates: list[DestinationDiscoveryCandidate] = Field(default_factory=list)


class DiscoverRegionResponse(BaseModel):
    job: RegionDiscoveryJob
    preview: RegionDiscoveryPreview | None = None


class JobDetailResponse(BaseModel):
    job: RegionDiscoveryJob
    preview: RegionDiscoveryPreview | None = None


class CandidateListResponse(BaseModel):
    items: list[DestinationDiscoveryCandidate]
    total: int


class BulkCreateOptions(BaseModel):
    create_default_scopes: bool = True
    include_boundary_buffer_scope: bool = True
    update_existing_scopes: bool = False
    queue_import: bool = False


class BulkCreateRequest(BaseModel):
    candidate_ids: list[str]
    options: BulkCreateOptions = Field(default_factory=BulkCreateOptions)
    idempotency_key: str | None = None


class CandidateCreateResult(BaseModel):
    candidate_id: str
    destination_slug: str | None = None
    status: Literal["created", "skipped_existing", "conflict", "error"]
    message: str
    created_scopes: list[str] = Field(default_factory=list)


class BulkCreateResult(BaseModel):
    total_requested: int
    created: int
    skipped_existing: int
    conflicts: int
    errors: int
    items: list[CandidateCreateResult]
    warnings: list[DiscoveryWarning] = Field(default_factory=list)
