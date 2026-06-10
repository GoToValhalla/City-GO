from __future__ import annotations

from datetime import datetime
from typing import List

from services.route_assembly_service import RoutePoint


class FinalRoute:
    def __init__(
        self,
        route_id: str,
        points: List[RoutePoint],
        total_minutes: int,
        total_places: int,
        estimated_distance: float,
        total_estimated_minutes: int = 0,
        estimated_end_time: datetime | None = None,
        has_warnings: bool = False,
        warning_count: int = 0,
        places_with_warnings: List[str] | None = None,
        warnings: List[str] | None = None,
        quality_score: float = 0.0,
        quality_status: str = "weak",
        quality_breakdown: dict[str, object] | None = None,
        pipeline_trace: list[dict[str, object]] | None = None,
        candidate_options: list[RoutePoint] | None = None,
        total_walk_distance_meters: int = 0,
        time_breakdown: dict[str, float] | None = None,
        category_distribution: dict[str, int] | None = None,
        status: str = "ready",
        partial_reason: str | None = None,
    ):
        self.route_id = route_id
        self.status = status
        self.partial_reason = partial_reason
        self.points = points
        self.total_minutes = total_minutes
        self.total_places = total_places
        self.estimated_distance = estimated_distance
        self.total_estimated_minutes = total_estimated_minutes
        self.estimated_end_time = estimated_end_time
        self.has_warnings = has_warnings
        self.warning_count = warning_count
        self.places_with_warnings = _list_or_empty(places_with_warnings)
        self.warnings = _list_or_empty(warnings)
        self.quality_score = quality_score
        self.quality_status = quality_status
        self.quality_breakdown = _dict_or_empty(quality_breakdown)
        self.pipeline_trace = _list_or_empty(pipeline_trace)
        self.candidate_options = _list_or_empty(candidate_options)
        self.total_walk_distance_meters = int(total_walk_distance_meters)
        self.time_breakdown = _dict_or_empty(time_breakdown)
        self.category_distribution = _dict_or_empty(category_distribution)


def _list_or_empty(value: list | None) -> list:
    return list(value) if value is not None else []


def _dict_or_empty(value: dict | None) -> dict:
    return dict(value) if value is not None else {}
