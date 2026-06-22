"""Схемы admin dry-run маршрутов."""

from __future__ import annotations

from pydantic import BaseModel, Field

from schemas.route import RouteDetailRead
from schemas.route_draft import RouteDraftRead


class AdminRouteDryRunRequest(BaseModel):
    city_slug: str
    duration_min: int = Field(default=180, ge=30, le=720)
    route_mode: str = Field(default="walk")
    interests: list[str] = Field(default_factory=list)
    avoided_categories: list[str] = Field(default_factory=list)
    budget_level: int | None = Field(default=None, ge=1, le=4)
    start_lat: float | None = None
    start_lng: float | None = None
    limit: int | None = Field(default=None, ge=1, le=20)


class AdminRouteDryRunCandidate(BaseModel):
    place_id: int
    title: str | None = None
    category: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_eligible: bool
    selected: bool
    score: float | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
    selection_reasons: list[str] = Field(default_factory=list)


class AdminRouteDryRunCounts(BaseModel):
    total_candidates: int
    eligible_candidates: int
    rejected_candidates: int
    selected_places: int


class AdminRouteDryRunResponse(BaseModel):
    request_summary: dict[str, object]
    generation_run_id: int
    selected_places: list[AdminRouteDryRunCandidate]
    rejected_candidates: list[AdminRouteDryRunCandidate]
    counts: AdminRouteDryRunCounts
    quality: dict[str, object] | None = None


class AdminRouteDraftGenerationResponse(BaseModel):
    draft: RouteDraftRead
    dry_run: AdminRouteDryRunResponse


class AdminRouteDraftPublishRequest(BaseModel):
    title: str | None = None
    slug: str | None = None
    reason: str | None = None


class AdminRouteDraftPublishResponse(BaseModel):
    draft_id: int
    route: RouteDetailRead
    message: str
