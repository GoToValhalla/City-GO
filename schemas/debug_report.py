from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["info", "warning", "error", "critical"]


class DebugReportCreate(BaseModel):
    screen: str = "unknown"
    severity: Severity = "info"
    category: str = "other"
    city_slug: str | None = None
    destination_slug: str | None = None
    place_id: int | None = None
    route_id: str | None = None
    request_id: str | None = None
    url: str | None = None
    user_action: str | None = None
    title: str = Field(default="Debug report", max_length=255)
    summary: str = Field(default="No summary", max_length=4000)
    user_comment: str | None = None
    frontend_state: dict[str, Any] | None = None
    request_payload: dict[str, Any] | None = None
    response_summary: dict[str, Any] | None = None
    response_payload: dict[str, Any] | None = None
    debug_trace: dict[str, Any] | list[Any] | None = None
    warnings: list[Any] | None = None
    reason_codes: list[Any] | None = None
    linked_entities: dict[str, Any] | None = None
    browser: dict[str, Any] | None = None
    location_context: dict[str, Any] | None = None
    backend_context: dict[str, Any] | None = None
    allow_precise_coordinates: bool = False


class DebugReportRead(BaseModel):
    id: int
    public_id: str
    created_at: datetime
    environment: str | None
    app_version: str | None
    screen: str
    severity: str
    category: str
    city_slug: str | None
    destination_slug: str | None
    place_id: int | None
    route_id: str | None
    request_id: str | None
    url: str | None
    user_action: str | None
    title: str
    summary: str
    user_comment: str | None
    frontend_state: dict[str, Any] | None
    request_payload: dict[str, Any] | None
    response_summary: dict[str, Any] | None
    response_payload: dict[str, Any] | None
    debug_trace: dict[str, Any] | list[Any] | None
    warnings: list[Any] | None
    reason_codes: list[Any] | None
    linked_entities: dict[str, Any] | None
    browser: dict[str, Any] | None
    location_context: dict[str, Any] | None
    backend_context: dict[str, Any] | None
    sanitized_payload: dict[str, Any]
    telegram_sent: bool
    telegram_error: str | None
    status: str

    model_config = ConfigDict(from_attributes=True)


class DebugReportCreateResponse(BaseModel):
    report_id: int
    public_id: str
    status: str = "accepted"
    telegram_status: str = "queued"


class DebugReportListResponse(BaseModel):
    items: list[DebugReportRead]
    total: int
    limit: int
    offset: int
