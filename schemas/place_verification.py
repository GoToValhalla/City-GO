from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlaceVerificationTaskRead(BaseModel):
    id: int
    place_id: int
    reason: str
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlaceVerificationEnqueueSummary(BaseModel):
    city_slug: str
    enqueued: int = 0
    already_pending: int = 0


class PlaceVerificationQueueItem(BaseModel):
    place_id: int
    title: str
    slug: str
    city_slug: str | None = None
    category: str | None = None
    address: str | None = None
    lat: float
    lng: float
    distance_meters: float | None = None
    existence_confidence_score: int
    existence_confidence_level: str
    verification_status: str
    verification_source: str | None = None
    verification_method: str | None = None
    verified_at: datetime | None = None
    verified_by: str | None = None
    needs_recheck_at: datetime | None = None
    verification_comment: str | None = None


class PlaceVerificationQueueResponse(BaseModel):
    items: list[PlaceVerificationQueueItem]
    total: int
    limit: int
    offset: int


class PlaceVerificationSummary(BaseModel):
    queue_total: int
    needs_recheck: int
    unverified: int
    low_confidence: int
    verified_today: int


class PlaceVerificationRequest(BaseModel):
    action: str = Field(pattern="^(exists|not_found|closed|moved|duplicate|needs_recheck)$")
    verifier: str | None = "local_admin"
    verifier_lat: float | None = None
    verifier_lng: float | None = None
    photo_url: str | None = None
    comment: str | None = None


class PlaceNearbyConfirmRequest(BaseModel):
    verifier: str | None = "local_admin"
    verifier_lat: float
    verifier_lng: float
    comment: str | None = None


class PlaceVerificationResult(BaseModel):
    place_id: int
    title: str
    status: str
    is_active: bool
    existence_confidence_score: int
    existence_confidence_level: str
    verification_status: str
    verification_source: str | None = None
    verification_method: str | None = None
    verified_at: datetime | None = None
    verified_by: str | None = None
    verification_comment: str | None = None


class PlaceVerificationStats(BaseModel):
    city_slug: str
    total_places: int
    verified_count: int
    high_count: int
    medium_count: int
    low_count: int
    unknown_count: int
    needs_recheck_count: int
    closed_count: int
    not_found_count: int
    verified_percent: float
    categories: dict[str, dict[str, int]]
