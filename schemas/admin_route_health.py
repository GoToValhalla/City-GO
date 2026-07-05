from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


RouteHealthSeverity = Literal["critical", "warning", "ok"]


class RouteHealthIssue(BaseModel):
    code: str
    label: str
    severity: RouteHealthSeverity
    route_id: int
    route_title: str
    details: dict[str, object]


class RouteHealthSummary(BaseModel):
    city_slug: str | None = None
    checked_at: datetime
    routes_checked: int
    critical_count: int
    warning_count: int
    status: Literal["healthy", "warning", "critical"]
    issues: list[RouteHealthIssue]


class RouteHealthRerunResponse(BaseModel):
    status: Literal["completed"]
    result: RouteHealthSummary
