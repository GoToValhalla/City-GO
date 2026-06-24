"""Contracts for admin operational center."""

from datetime import datetime

from pydantic import BaseModel, Field


class AlertTransitionRequest(BaseModel):
    status: str = Field(pattern="^(acknowledged|resolved|open)$")


class AlertRead(BaseModel):
    id: int
    severity: str
    status: str
    module: str
    message: str
    city_slug: str | None = None
    request_id: str | None = None
    created_at: datetime


class AlertListResponse(BaseModel):
    items: list[AlertRead]
    total: int


class PlatformPayload(BaseModel):
    data: dict[str, object]
