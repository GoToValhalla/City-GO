from datetime import datetime

from pydantic import BaseModel, Field


class RouteAnalyticsSummary(BaseModel):
    total_routes: int = 0
    average_quality_score: float = 0.0
    warning_rate: float = 0.0
    average_latency_ms: float = 0.0
    by_source: dict[str, int] = Field(default_factory=dict)


class UserRouteHistoryItem(BaseModel):
    route_id: str
    source: str
    city_id: str | None = None
    total_places: int = 0
    quality_score: float = 0.0
    warning_count: int = 0
    created_at: datetime
