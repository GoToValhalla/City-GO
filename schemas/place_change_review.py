from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AdminPlaceChangeReviewRead(BaseModel):
    id: int
    city_slug: str
    city_name: str
    place_id: int
    place_title: str
    reason: str
    severity: str
    status: str
    decision: str
    changes: dict[str, Any] = Field(default_factory=dict)
    review_reasons: list[str] = Field(default_factory=list)
    created_at: datetime
    resolved_at: datetime | None = None
    resolution: str | None = None


class AdminPlaceChangeReviewListResponse(BaseModel):
    items: list[AdminPlaceChangeReviewRead]
    total: int
    limit: int
    offset: int


class AdminPlaceChangeReviewActionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class AdminPlaceChangeReviewActionResponse(BaseModel):
    item: AdminPlaceChangeReviewRead
    message: str
