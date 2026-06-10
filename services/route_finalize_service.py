from uuid import uuid4

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint
from services.route_finalize_metrics import (
    compute_distance,
    compute_time_aware_span,
    compute_total_time,
)
from services.route_finalize_types import FinalRoute
from services.route_finalize_warnings import route_level_warning_strings, time_warned_place_ids
from services.route_quality_score import build_route_quality_score, public_quality_warnings
from services.route_response_metrics import route_category_distribution, time_breakdown
from services.route_status_service import partial_reason, route_status


class RouteFinalizeService:
    def finalize(
        self,
        route: list[RoutePoint],
        ctx: MergedContext,
        extra_warnings: list[str] | None = None,
    ) -> FinalRoute:

        route_warnings = route_level_warning_strings(route, extra_warnings)
        status = route_status(len(route), ctx.effective_num_stops)
        reason = partial_reason(status, route_warnings)

        if not route:
            return self._empty_route(route_warnings, status, reason)

        total_minutes = compute_total_time(route)
        total_places = len(route)
        total_distance = compute_distance(route, ctx)
        total_estimated_minutes, estimated_end_time = compute_time_aware_span(route)
        time_bad_ids = time_warned_place_ids(route)
        quality = build_route_quality_score(
            route,
            ctx.effective_num_stops,
            ctx.effective_time_budget_minutes,
            route_warnings,
        )
        public_warnings = public_quality_warnings(route, ctx.effective_time_budget_minutes, route_warnings)

        has_warnings = len(time_bad_ids) > 0 or len(public_warnings) > 0
        warning_count = len(time_bad_ids) + len(public_warnings)

        route_id = str(uuid4())

        return FinalRoute(
            route_id=route_id,
            status=status,
            partial_reason=reason,
            points=route,
            total_minutes=total_minutes,
            total_places=total_places,
            estimated_distance=total_distance,
            total_estimated_minutes=total_estimated_minutes,
            estimated_end_time=estimated_end_time,
            has_warnings=has_warnings,
            warning_count=warning_count,
            places_with_warnings=time_bad_ids,
            warnings=public_warnings,
            quality_score=quality.score,
            quality_status=quality.status,
            quality_breakdown=quality.as_dict(),
            total_walk_distance_meters=int(round(total_distance * 1000)),
            time_breakdown=time_breakdown(route, ctx.effective_time_budget_minutes),
            category_distribution=route_category_distribution(route),
        )

    def _empty_route(self, warnings: list[str], status: str, reason: str | None) -> FinalRoute:
        quality = build_route_quality_score([], 0, 0, warnings)
        public_warnings = public_quality_warnings([], 0, warnings)
        return FinalRoute(
            route_id=str(uuid4()),
            status=status,
            partial_reason=reason,
            points=[],
            total_minutes=0,
            total_places=0,
            estimated_distance=0.0,
            total_estimated_minutes=0,
            estimated_end_time=None,
            has_warnings=bool(public_warnings),
            warning_count=len(public_warnings),
            places_with_warnings=[],
            warnings=public_warnings,
            quality_score=quality.score,
            quality_status=quality.status,
            quality_breakdown=quality.as_dict(),
            total_walk_distance_meters=0,
            time_breakdown=time_breakdown([], 0),
            category_distribution={},
        )
