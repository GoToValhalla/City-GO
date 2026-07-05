from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class EmergencyHideRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=1000)
    idempotency_key: str = Field(min_length=8, max_length=128)


class EmergencyHideResponse(BaseModel):
    place_id: int
    status: str
    publication_status: str
    is_published: bool
    is_visible_in_catalog: bool
    is_route_eligible: bool
    audit_log_id: int
    idempotent_replay: bool = False
    reason: str
    hidden_at: datetime
