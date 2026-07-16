from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from schemas.user_profile import UserProfile
from services.context_merge_service import RequestContext
from services.place_runtime_defaults import apply_runtime_place_defaults
from services.place_validation_service import validate_place
from services.route_adaptive_plan import prepare_route_plan
from services.route_adaptive_types import RoutePlan
from services.route_assembly_service import RoutePoint
from services.route_budget_fit_service import BudgetFitResult
from services.route_candidate_diagnostics import candidate_diagnostics
from services.route_generation_diagnostics.record import record_canonical_generation
from services.route_geometry import walk_minutes_between
from services.route_pipeline_trace import RoutePipelineTrace, log_route_trace, timed_trace, top_scores
from services.route_pipeline_warnings import assembly_warnings, candidate_warnings, filter_warnings
from services.route_point_factory import route_point_from_scored, visit_minutes_for_scored
from services.route_quality_gates import evaluate_quality_gates
from services.route_quality_warnings import route_quality_warnings
from services.route_start_time import effective_route_start

MAX_CANDIDATE_OPTIONS = 40
SOFT_BUDGET_FILL_RATIO = 0.9
HARD_BUDGET_FILL_RATIO = 1.0
DEBUG_SAMPLE_LIMIT = 12


def build_dynamic_route(
    deps: object,
    db: Session,
    request: RequestContext,
    profile: UserProfile | None,
) -> object:
    trace = RoutePipelineTrace()
    trace.add(
        "debug_route_contract",
        purpose="temporary_full_route_chain_debug_visible_in_ui",
        expected_chain="context -> retrieval -> hard_filters -> scoring -> interest_matching -> adaptive_plan -> assembly -> time_ordering -> time_aware -> budget_fit -> quality_gates -> finalize -> final",
    )
    ctx = _ctx(deps, request, profile, trace)
    now = effective_route_start(datetime.utcnow(), getattr(ctx, "time_of_day", None))
    trace.add(
        "route_start_time",
        now_iso=now.isoformat(),
        route_time_mode=getattr(ctx, "route_time_mode", None),
        time_of_day=getattr(ctx, "time_of_day", None),
    )
    candidates, input_warnings, diagnostics = _candidates(deps, db, ctx, trace)
    filtered, filtered_warnings = _filtered(deps, candidates, ctx, now, trace)
    scored = _scored(deps, filtered, ctx, trace)
    plan = _planned(scored, ctx, trace)
    route, route_warnings = _route(deps, plan.scored, filtered, ctx, now, trace, plan.target_points)
    budget_fit = _budget_fit(deps, route, plan.scored, ctx, trace)
    gate = evaluate_quality_gates(
        budget_fit.route,
        plan,
        diagnostics,
        list(getattr(ctx, "avoided_place_ids", []) or []),
        list(getattr(ctx, "avoided_categories", []) or []),
        bool(route and not budget_fit.route),
    )
    trace.add(
        "quality_gates",
        status=gate.route_quality_status,
        input_count=len(budget_fit.route),
        output_count=len(budget_fit.route),
        route_quality_status=gate.route_quality_status,
        route_completeness=gate.route_completeness,
        fallback_level=gate.fallback_level,
        failed_gates=gate.warnings,
        user_explanation=plan.user_explanation,
        warnings=gate.warnings[:DEBUG_SAMPLE_LIMIT],
    )
    warnings = _unique(
        [
            *_interest_normalization_warnings(ctx),
            *input_warnings,
            *filtered_warnings,
            *route_warnings,
            *plan.warnings,
            *gate.warnings,
            *route_quality_warnings(budget_fit.route, plan.target_points),
            *budget_fit.warnings,
        ]
    )
    final_route = deps.finalize.finalize(budget_fit.route, ctx, extra_warnings=warnings)
    _apply_adaptive_metadata(final_route, plan, gate, ctx)
    trace.add(
        "finalize",
        input_count=len(budget_fit.route),
        final_places_count=len(getattr(final_route, "places", []) or []),
        final_total_minutes=getattr(final_route, "total_duration_minutes", None),
        final_total_km=getattr(final_route, "total_distance_km", None),
        partial_reason=getattr(final_route, "partial_reason", None),
        warning_count=len(getattr(final_route, "warnings", []) or []),
        warnings=list(getattr(final_route, "warnings", []) or [])[:DEBUG_SAMPLE_LIMIT],
        final_points=_route_point_sample(getattr(final_route, "places", []) or []),
    )
    final_route.pipeline_trace = trace.snapshot()
    final_route.candidate_options = _candidate_options(scored, ctx, budget_fit.route)
    final_route.generation_run_id = _record_generation(db, ctx, request, final_route)
    trace.add("generation_record", generation_run_id=final_route.generation_run_id)
    trace.add(
        "final",
        final_points_count=len(getattr(final_route, "points", []) or []),
        final_duration_minutes=getattr(final_route, "total_estimated_minutes", None)
        or getattr(final_route, "total_minutes", None),
        final_distance_km=getattr(final_route, "estimated_distance", None),
        final_place_ids=[str(getattr(point, "place_id", "")) for point in getattr(final_route, "points", []) or []],
        failure_stage=_failure_stage(candidates, filtered, scored, route, budget_fit.route, gate),
    )
    trace.add(
        "final_response",
        input_count=len(budget_fit.route),
        output_count=len(getattr(final_route, "places", []) or getattr(final_route, "points", []) or []),
        route_quality_status=getattr(final_route, "route_quality_status", None),
        route_completeness=getattr(final_route, "route_completeness", None),
        warnings=list(getattr(final_route, "warnings", []) or [])[:DEBUG_SAMPLE_LIMIT],
    )
    final_route.pipeline_trace = trace.snapshot()
    log_route_trace(str(final_route.route_id), trace)
    return final_route


def _record_generation(db: Session, ctx: object, request: RequestContext, final_route: object) -> int | None:
    city = db.query(City).filter(City.slug == str(getattr(ctx, "city_id", "") or "")).first()
    payload = {
        "city_id": getattr(ctx, "city_id", None),
        "time_budget_minutes": getattr(ctx, "effective_time_budget_minutes", None),
        "interests": list(getattr(ctx, "interests", []) or []),
        "location": list(getattr(ctx, "location", ()) or ()),
        "radius_meters": getattr(ctx, "radius_meters", None),
        "request": request.model_dump() if hasattr(request, "model_dump") else {},
    }
    return record_canonical_generation(db, city=city, ctx=ctx, request_payload=payload, final_route=final_route)


def _ctx(deps: object, request: RequestContext, profile: UserProfile | None, trace: RoutePipelineTrace):
    started = perf_counter()
    ctx = deps.context_merge.merge(request, profile)
    timed_trace(
        trace,
        "context_merge",
        started,
        city_id=getattr(ctx, "city_id", None),
        location=list(getattr(ctx, "location", ()) or ()),
        radius_meters=getattr(ctx, "radius_meters", None),
        requested_budget_minutes=getattr(request, "time_budget_minutes", None),
        effective_time_budget_minutes=getattr(ctx, "effective_time_budget_minutes", None),
        time_budget_minutes=getattr(ctx, "time_budget_minutes", None),
        budget_minutes_for_pipeline=_budget_minutes(ctx),
        hard_budget_minutes=_hard_budget_minutes(ctx),
        soft_budget_minutes=_soft_budget_minutes(ctx),
        effective_num_stops=getattr(ctx, "effective_num_stops", None),
        min_stop_duration_minutes=getattr(ctx, "min_stop_duration_minutes", None),
        pace_multiplier=getattr(ctx, "pace_multiplier", None),
        budget_level=getattr(ctx, "budget_level", None),
        route_time_mode=getattr(ctx, "route_time_mode", None),
        time_of_day=getattr(ctx, "time_of_day", None),
        interests=list(getattr(ctx, "interests", []) or []),
        interest_removed_due_to_avoidance=list(getattr(ctx, "interest_removed_due_to_avoidance", []) or []),
        avoided_categories=list(getattr(ctx, "avoided_categories", []) or []),
        excluded_place_ids=list(getattr(ctx, "excluded_place_ids", []) or []),
    )
    trace.add(
        "context",
        city_id=getattr(ctx, "city_id", None),
        start_lat=_start_lat(ctx),
        start_lng=_start_lng(ctx),
        radius_meters=getattr(ctx, "radius_meters", None),
        time_budget_minutes=getattr(ctx, "time_budget_minutes", None),
        route_time_mode=getattr(ctx, "route_time_mode", None),
        time_of_day=getattr(ctx, "time_of_day", None),
        interests=list(getattr(ctx, "interests", []) or []),
        interest_removed_due_to_avoidance=list(getattr(ctx, "interest_removed_due_to_avoidance", []) or []),
        avoided_categories=list(getattr(ctx, "avoided_categories", []) or []),
        excluded_place_ids=list(getattr(ctx, "avoided_place_ids", []) or []),
        budget_level=getattr(ctx, "budget_level", None),
        pace_mode=getattr(ctx, "pace_mode", None),
    )
    trace.add(
        "context_normalization",
        input_count=1,
        output_count=1,
        city_id=getattr(ctx, "city_id", None),
        total_requested_interests=len(list(getattr(ctx, "interests", []) or [])),
        interests=list(getattr(ctx, "interests", []) or []),
        interest_removed_due_to_avoidance=list(getattr(ctx, "interest_removed_due_to_avoidance", []) or []),
        warnings=_interest_normalization_warnings(ctx),
    )
    return ctx


def _candidates(deps: object, db: Session, ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    candidates = deps.retrieval.get_candidates(db, ctx)
    diagnostics = candidate_diagnostics(db, ctx)
    trace.add("city_stats", **_city_stats_payload(diagnostics))
    trace.add("retrieval", **_retrieval_payload(deps, ctx, candidates, diagnostics))
    timed_trace(
        trace,
        "candidate_retrieval",
        started,
        count=len(candidates),
        categories=_category_counts(candidates),
        sample_candidates=_place_sample(candidates, ctx),
        **diagnostics,
    )
    started = perf_counter()
    annotated = list(map(_annotate_quality, candidates))
    warnings = candidate_warnings(annotated)
    timed_trace(
        trace,
        "quality_annotation",
        started,
        input_count=len(candidates),
        output_count=len(annotated),
        warning_count=len(warnings),
        warnings=warnings[:DEBUG_SAMPLE_LIMIT],
        validation_issue_counts=_validation_issue_counts(annotated),
        sample_candidates=_place_sample(annotated, ctx),
    )
    return annotated, warnings, diagnostics


def _filtered(deps: object, candidates: list[object], ctx: object, now: datetime, trace: RoutePipelineTrace):
    started = perf_counter()
    report = deps.filters.apply_with_report(candidates, ctx, now)
    warnings = filter_warnings(candidates, report.kept)
    kept = report.kept
    timed_trace(
        trace,
        "hard_filter",
        started,
        input_count=len(candidates),
        strict_kept_count=report.strict_kept_count,
        relaxed_kept_count=report.relaxed_kept_count,
        kept_count=len(kept),
        original_kept_count=len(report.kept),
        removed_count=len(report.rejected),
        fallback_used=report.fallback_used,
        reasons=report.reason_counts,
        strict_removal_reasons=report.strict_reason_counts,
        relaxed_removal_reasons=report.relaxed_reason_counts,
        kept_categories=_category_counts(kept),
        kept_sample=_place_sample(kept, ctx),
        rejected_sample=_rejected_sample(report.rejected, ctx),
        warnings=warnings[:DEBUG_SAMPLE_LIMIT],
    )
    trace.add(
        "hard_filters",
        input_count=len(candidates),
        strict_kept=report.strict_kept_count,
        relaxed_kept=report.relaxed_kept_count,
        fallback_used=report.fallback_used,
        output_count=len(kept),
        removed_count=len(report.rejected),
        removal_reasons=report.reason_counts,
        strict_removal_reasons=report.strict_reason_counts,
        relaxed_removal_reasons=report.relaxed_reason_counts,
        sample_removed=_filter_removed_sample(candidates, report.rejected),
    )
    trace.add(
        "hard_filtering",
        input_count=len(candidates),
        output_count=len(kept),
        drop_reason=report.reason_counts,
        warnings=warnings[:DEBUG_SAMPLE_LIMIT],
    )
    return kept, warnings


def _scored(deps: object, filtered: list[object], ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    scored = deps.scoring.score(filtered, ctx)
    timed_trace(
        trace,
        "scoring_raw",
        started,
        input_count=len(filtered),
        count=len(scored),
        top3_scores=top_scores(scored),
        score_min=_score_min(scored),
        score_max=_score_max(scored),
        categories=_scored_category_counts(scored),
        top_scored=_scored_sample(scored, ctx),
    )
    return scored


def _planned(scored: list[object], ctx: object, trace: RoutePipelineTrace) -> RoutePlan:
    plan = prepare_route_plan(scored, ctx)
    trace.add("scoring", **_scoring_payload(plan.scored, ctx))
    trace.add(
        "interest_matching",
        input_count=len(scored),
        requested_interests=list(getattr(ctx, "interests", []) or []),
        interest_removed_due_to_avoidance=list(getattr(ctx, "interest_removed_due_to_avoidance", []) or []),
        exact_count=plan.exact_count,
        exact_matches_count=plan.exact_count,
        related_matches_count=plan.related_count,
        neutral_candidates_count=plan.neutral_count,
        expansion_level=plan.expansion_level,
        expanded_category_count=plan.expanded_category_count,
        neutral_added_count=plan.neutral_added_count,
        output_count=plan.expanded_pool_count,
        target_points=plan.target_points,
        matched_interest_count=plan.exact_count,
        total_requested_interests=len(list(getattr(ctx, "interests", []) or [])),
        related_count=plan.related_count,
        neutral_count=plan.neutral_count,
        sample_exact_ids=_sample_ids_by_point_type(plan.scored, "primary"),
        sample_related_ids=_sample_ids_by_point_type(plan.scored, "related"),
        sample_neutral_ids=_sample_ids_by_point_type(plan.scored, "neutral"),
        warnings=plan.warnings[:DEBUG_SAMPLE_LIMIT],
    )
    trace.add(
        "adaptive_plan",
        input_count=len(scored),
        output_count=len(plan.scored),
        target_points=plan.target_points,
        expansion_level=plan.expansion_level,
        exact_count=plan.exact_count,
        related_count=plan.related_count,
        neutral_count=plan.neutral_count,
        expanded_category_count=plan.expanded_category_count,
        neutral_added_count=plan.neutral_added_count,
        user_explanation=plan.user_explanation,
        warnings=plan.warnings[:DEBUG_SAMPLE_LIMIT],
    )
    trace.add(
        "pool_expansion",
        input_count=plan.exact_count,
        output_count=plan.expanded_pool_count,
        expansion_level=plan.expansion_level,
        expanded_category_count=plan.expanded_category_count,
        neutral_added_count=plan.neutral_added_count,
        target_points=plan.target_points,
        warnings=plan.warnings[:DEBUG_SAMPLE_LIMIT],
    )
    return plan


def _route(deps: object, scored: list[object], filtered: list[object], ctx: object, now: datetime, trace: RoutePipelineTrace, target_points: int):
    started = perf_counter()
    trace.add(
        "assembly_input_debug",
        scored_count=len(scored),
        filtered_count=len(filtered),
        budget_minutes=_budget_minutes(ctx),
        top_scored=_scored_sample(scored, ctx),
        first_point_fit_debug=_first_point_fit_debug(scored, ctx),
    )
    route = deps.assembly.build(scored, ctx)
    fallback_used = False
    if not route and scored:
        route = _minimal_route_from_scored(scored, ctx, target_points)
        fallback_used = bool(route)
    warnings = assembly_warnings(filtered, route)
    if fallback_used:
        warnings = _unique([*warnings, "assembly_zero_recovered_by_minimal_fallback"])
    original_selected_count = len(route)
    first_point_debug = _first_point_fit_debug(scored, ctx)
    selected_ids = _route_ids(route)
    rejected_count = max(0, len(scored) - len(selected_ids))
    first_point_reasons = _first_point_rejection_reasons(first_point_debug)
    timed_trace(
        trace,
        "assembly",
        started,
        selected_count=len(route),
        original_selected_count=original_selected_count,
        warning_count=len(warnings),
        input_count=len(scored),
        input_scored_count=len(scored),
        target_points=target_points,
        selected_count_before_budget=len(route),
        rejected_count=rejected_count,
        rejection_reasons=_assembly_rejection_reasons(rejected_count),
        selected_ids=selected_ids,
        rejected_sample=_assembly_rejected_sample(scored, selected_ids),
        first_point_candidates_checked=first_point_debug.get("checked_count", 0),
        first_point_rejection_reasons=first_point_reasons,
        failure_reason=_assembly_failure_reason(route, scored, first_point_reasons),
        fallback_used=fallback_used,
        fallback_triggers=["assembly_selected_zero"] if fallback_used else [],
        route_minutes=_route_minutes(route),
        original_route_sample=_route_point_sample(route),
        route_sample=_route_point_sample(route),
        warnings=warnings[:DEBUG_SAMPLE_LIMIT],
    )
    before_time_ordering = list(route)
    ordered_route = deps.time_ordering.order(route, ctx, now)
    trace.add("time_ordering", input_count=len(before_time_ordering), output_count=len(ordered_route), input_route=_route_point_sample(before_time_ordering), output_route=_route_point_sample(ordered_route))
    before_time_apply = list(ordered_route)
    route = deps.time.apply(ordered_route, ctx, now)
    timed_trace(
        trace,
        "time_aware",
        started,
        input_count=len(before_time_apply),
        output_count=len(route),
        count=len(route),
        removed_count=max(0, len(before_time_apply) - len(route)),
        route_minutes=_route_minutes(route),
        input_route=_route_point_sample(before_time_apply),
        output_route=_route_point_sample(route),
    )
    return route, warnings


def _budget_fit(deps: object, route: list[object], scored: list[object], ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    first_fit = deps.budget_fit.fit(route, ctx)
    removed_by_budget = _removed_by_budget(route, first_fit.route)
    trace.add("budget_fit_first", input_count=len(route), kept_count=len(first_fit.route), warning_count=len(first_fit.warnings), input_minutes=_route_minutes(route), kept_minutes=_route_minutes(first_fit.route), warnings=list(first_fit.warnings)[:DEBUG_SAMPLE_LIMIT], input_route=_route_point_sample(route), kept_route=_route_point_sample(first_fit.route))
    trace.add(
        "budget_gap_fill",
        input_count=len(first_fit.route),
        scored_count=len(scored),
        output_count=len(first_fit.route),
        added_count=0,
        input_minutes=_route_minutes(first_fit.route),
        output_minutes=_route_minutes(first_fit.route),
        route_sample=_route_point_sample(first_fit.route),
        remaining_top_scored=_scored_sample([item for item in scored if str(getattr(item.place, "id", "")) not in {str(getattr(point, "place_id", "")) for point in first_fit.route}], ctx),
    )
    final_fit = first_fit
    if route and not final_fit.route:
        final_fit = BudgetFitResult([route[0]], _unique([*final_fit.warnings, "budget_fit_recovered_first_point"]))
    timed_trace(
        trace,
        "budget_fit",
        started,
        input_count=len(route),
        output_count=len(final_fit.route),
        kept_count=len(final_fit.route),
        warning_count=len(final_fit.warnings),
        requested_budget_minutes=_budget_minutes(ctx),
        actual_duration_minutes=_route_minutes(final_fit.route),
        route_completeness=_route_completeness(final_fit.route, len(route)),
        removed_by_budget_count=len(removed_by_budget),
        removed_by_budget_sample=_route_point_sample(removed_by_budget),
        failure_reason=_budget_failure_reason(route, final_fit.route),
        before_fit_input_count=len(route),
        before_fill_count=len(first_fit.route),
        after_fill_count=len(first_fit.route),
        route_minutes=_route_minutes(final_fit.route),
        target_minutes=_soft_budget_minutes(ctx),
        hard_budget_minutes=_hard_budget_minutes(ctx),
        warnings=list(final_fit.warnings)[:DEBUG_SAMPLE_LIMIT],
        final_route_sample=_route_point_sample(final_fit.route),
    )
    return final_fit


def _candidate_options(scored: list[object], ctx: object, route: list[object]) -> list[RoutePoint]:
    selected_ids = {str(getattr(point, "place_id", "")) for point in route}
    options: list[RoutePoint] = []
    for item in scored:
        point = route_point_from_scored(item, ctx, RoutePoint)
        if str(point.place_id) not in selected_ids:
            options.append(point)
        if len(options) >= MAX_CANDIDATE_OPTIONS:
            break
    return options


def _minimal_route_from_scored(scored: list[object], ctx: object, target_points: int) -> list[RoutePoint]:
    limit = max(1, min(2, target_points or 1))
    route: list[RoutePoint] = []
    used_ids: set[str] = set()
    for item in _fallback_order(scored, ctx):
        place_id = str(getattr(getattr(item, "place", None), "id", "") or "")
        if not place_id or place_id in used_ids:
            continue
        tail_lat, tail_lng = _tail_location(route, ctx)
        point = route_point_from_scored(item, ctx, RoutePoint)
        point.estimated_walk_minutes = walk_minutes_between(tail_lat, tail_lng, point.lat, point.lng)
        route.append(point)
        used_ids.add(place_id)
        if len(route) >= limit:
            break
    return route


def _fallback_order(scored: list[object], ctx: object) -> list[object]:
    lat, lng = getattr(ctx, "location", (None, None))
    return sorted(list(scored or []), key=lambda item: (-_score(item), _walk_from(lat, lng, item)))


def _score(item: object) -> float:
    return float(getattr(item, "score", 0.0) or 0.0)


def _walk_from(lat: object, lng: object, item: object) -> int:
    place = getattr(item, "place", None)
    if lat is None or lng is None or place is None:
        return 999_999
    return walk_minutes_between(float(lat), float(lng), float(place.lat), float(place.lng))


def _city_stats_payload(diagnostics: dict[str, object]) -> dict[str, object]:
    keys = ("places_total_in_city", "places_public_catalog", "places_route_eligible", "places_active_legacy_safe")
    return {key: diagnostics.get(key) for key in keys}


def _retrieval_payload(deps: object, ctx: object, candidates: list[object], diagnostics: dict[str, object]) -> dict[str, object]:
    debug = dict(getattr(getattr(deps, "retrieval", None), "last_debug", {}) or {})
    final_count = int(debug.get("final_candidates_count") or len(candidates))
    return {
        "input_city_id": getattr(ctx, "city_id", None),
        "requested_radius_meters": getattr(ctx, "radius_meters", None),
        "query_limit": debug.get("query_limit"),
        "healthy_min_candidates": debug.get("healthy_min_candidates"),
        "raw_candidates_count": debug.get("raw_candidates_count", len(candidates)),
        "after_radius_count": debug.get("after_radius_count", debug.get("raw_candidates_count", len(candidates))),
        "expanded_radius_candidates_count": debug.get("expanded_radius_candidates_count"),
        "city_wide_candidates_count": debug.get("city_wide_candidates_count"),
        "retrieval_strategy_used": debug.get("retrieval_strategy_used"),
        "retrieval_coverage_pct": debug.get("retrieval_coverage_pct"),
        "low_coverage_threshold_pct": debug.get("low_coverage_threshold_pct"),
        "after_city_filter_count": debug.get("city_scope_total", diagnostics.get("places_total_in_city")),
        "after_route_eligible_count": debug.get("route_eligible_before_user_exclusions", diagnostics.get("places_route_eligible")),
        "after_public_catalog_count": diagnostics.get("places_public_catalog"),
        "after_coordinates_count": diagnostics.get("places_with_coords"),
        "after_excluded_place_ids_count": debug.get("route_eligible_after_user_exclusions", final_count),
        "after_avoided_categories_count": debug.get("route_eligible_after_user_exclusions", final_count),
        "final_candidates_count": final_count,
        "fallback_city_wide_used": bool(debug.get("fallback_city_wide_used", False)),
        "fallback_radius_used": bool(debug.get("fallback_radius_used", False)),
        "center_used": debug.get("center_used"),
        "places_within_500m": debug.get("places_within_500m"),
        "places_within_1km": debug.get("places_within_1km"),
        "places_within_2km": debug.get("places_within_2km"),
        "places_within_5km": debug.get("places_within_5km"),
        "places_within_10km": debug.get("places_within_10km"),
        "city_wide_eligible": debug.get("city_wide_eligible"),
        "route_eligible_before_user_exclusions": debug.get("route_eligible_before_user_exclusions"),
        "route_eligible_after_user_exclusions": debug.get("route_eligible_after_user_exclusions"),
        "radius_before_user_exclusions": debug.get("radius_before_user_exclusions"),
        "radius_after_user_exclusions": debug.get("radius_after_user_exclusions"),
        "expanded_radius_meters": debug.get("expanded_radius_meters"),
        "expanded_radius_before_user_exclusions": debug.get("expanded_radius_before_user_exclusions"),
        "expanded_radius_after_user_exclusions": debug.get("expanded_radius_after_user_exclusions"),
        "city_wide_after_user_exclusions": debug.get("city_wide_after_user_exclusions"),
        "lost_by_user_exclusions_city_wide": debug.get("lost_by_user_exclusions_city_wide"),
        "lost_by_user_exclusions_radius": debug.get("lost_by_user_exclusions_radius"),
        "applied_avoided_categories": debug.get("applied_avoided_categories"),
        "applied_avoided_place_ids_count": debug.get("applied_avoided_place_ids_count"),
        "retrieval_loss_summary": debug.get("retrieval_loss_summary"),
        "final_candidate_categories": debug.get("final_candidate_categories"),
        "spatial_density": debug.get("spatial_density"),
        "retrieval_counts": debug.get("retrieval_counts"),
        "top_candidate_distances_meters": list(debug.get("top_candidate_distances_meters", []) or []),
        "sample_candidate_ids": list(debug.get("sample_candidate_ids", []) or []),
        "sample_candidates": list(debug.get("sample_candidates", []) or []),
    }


def _filter_removed_sample(candidates: list[object], rejected: object, limit: int = 10) -> list[dict[str, object]]:
    by_id = {str(getattr(place, "id", "")): place for place in candidates}
    rows = []
    for item in list(rejected or [])[:limit]:
        place = by_id.get(str(getattr(item, "place_id", "")))
        rows.append({"id": str(getattr(item, "place_id", "")), "name": _text(getattr(place, "title", None) or getattr(place, "name", None)) if place else None, "category": _text(getattr(place, "category", None)) if place else None, "reason": getattr(item, "reason", None)})
    return rows


def _scoring_payload(scored: list[object], ctx: object) -> dict[str, object]:
    scores = [float(getattr(item, "score", 0.0) or 0.0) for item in scored]
    return {"input_count": len(scored), "output_count": len(scored), "min_score": round(min(scores), 4) if scores else None, "max_score": round(max(scores), 4) if scores else None, "avg_score": round(sum(scores) / len(scores), 4) if scores else None, "top_scored_candidates": _top_scored_candidates(scored, ctx)}


def _top_scored_candidates(scored: list[object], ctx: object) -> list[dict[str, object]]:
    return [_scored_debug_row(item, ctx) for item in list(scored or [])[:10]]


def _scored_debug_row(item: object, ctx: object) -> dict[str, object]:
    place = getattr(item, "place", None)
    breakdown = dict(getattr(item, "breakdown", {}) or {})
    return {"id": str(getattr(place, "id", "") or ""), "name": _text(getattr(place, "title", None) or getattr(place, "name", None)), "category": _text(getattr(place, "category", None)), "score": round(float(getattr(item, "score", 0.0) or 0.0), 4), "distance_meters": _distance_meters_from_ctx(place, ctx), "point_type": breakdown.get("route_match_type")}


def _apply_adaptive_metadata(final_route: object, plan: RoutePlan, gate: object, ctx: object) -> None:
    fields = {"route_quality_status": getattr(gate, "route_quality_status", "unknown"), "route_completeness": getattr(gate, "route_completeness", 0.0), "matched_interest_count": plan.exact_count, "total_requested_interests": len(list(getattr(ctx, "interests", []) or [])), "expansion_level": plan.expansion_level, "expanded_category_count": plan.expanded_category_count, "neutral_added_count": plan.neutral_added_count, "fallback_level": getattr(gate, "fallback_level", "unknown"), "user_explanation": plan.user_explanation}
    for name, value in fields.items():
        setattr(final_route, name, value)
    status = str(fields["route_quality_status"])
    # route_quality_status == "failed" is returned by evaluate_quality_gates
    # for two genuinely different situations (services/route_quality_gates.py
    # ::_status): an assembled route that violates an explicit user exclusion
    # (a real algorithm bug — there IS a route, and it should not exist) and
    # a route with zero points (`if not route: return "failed"` — an honest
    # "no eligible candidates were found", already correctly reported by
    # RouteFinalizeService/route_status_service.route_status() as
    # final_route.status == "no_route"). Only the first case is an actual
    # failure; forcing final_route.status = "failed" for the second case
    # overwrote the honest "no_route" status with a misleading "failed" one
    # for the ordinary, expected empty-city/empty-radius outcome — this is
    # the exact HTTP 200 status=failed/quality_status=failed/total_places=0
    # production symptom. Only override when the route actually has points
    # (the exclusion-violation case) or the algorithm genuinely errored.
    if status == "algorithm_error" or (status == "failed" and getattr(final_route, "total_places", 0)):
        final_route.status = "failed"
    elif status in {"partial", "degraded"} and getattr(final_route, "total_places", 0):
        final_route.status = "partial_route"
    if getattr(gate, "partial_reason", None):
        final_route.partial_reason = getattr(gate, "partial_reason")


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(item for item in values if item))


def _interest_normalization_warnings(ctx: object) -> list[str]:
    removed = list(getattr(ctx, "interest_removed_due_to_avoidance", []) or [])
    return ["interest_removed_due_to_avoidance"] if removed else []


def _sample_ids_by_point_type(scored: list[object], point_type: str) -> list[str]:
    return [str(getattr(getattr(item, "place", None), "id", "")) for item in scored if dict(getattr(item, "breakdown", {}) or {}).get("route_match_type") == point_type][:10]


def _route_ids(route: list[object]) -> list[str]:
    return [str(getattr(point, "place_id", "")) for point in route]


def _assembly_rejected_sample(scored: list[object], selected_ids: list[str]) -> list[dict[str, object]]:
    selected = set(selected_ids)
    rows = []
    for item in scored:
        place = getattr(item, "place", None)
        place_id = str(getattr(place, "id", "") or "")
        if place_id in selected:
            continue
        rows.append({"id": place_id, "name": _text(getattr(place, "title", None) or getattr(place, "name", None)), "category": _text(getattr(place, "category", None)), "reason": "not_selected_by_optimizer"})
        if len(rows) >= 10:
            break
    return rows


def _assembly_rejection_reasons(rejected_count: int) -> dict[str, int]:
    return {"not_selected_by_optimizer": rejected_count} if rejected_count > 0 else {}


def _first_point_rejection_reasons(debug: dict[str, object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in list(debug.get("closest_candidates", []) or []):
        if not isinstance(row, dict):
            continue
        for reason in list(row.get("reject_reasons_if_first", []) or []):
            key = str(reason)
            counts[key] = counts.get(key, 0) + 1
    return counts


def _assembly_failure_reason(route: list[object], scored: list[object], first_point_reasons: dict[str, int]) -> str | None:
    if route:
        return None
    if not scored:
        return "no_scored_candidates"
    if first_point_reasons:
        return "first_point_candidates_rejected"
    return "optimizer_selected_zero_points"


def _removed_by_budget(input_route: list[object], output_route: list[object]) -> list[object]:
    kept = {str(getattr(point, "place_id", "")) for point in output_route}
    return [point for point in input_route if str(getattr(point, "place_id", "")) not in kept]


def _budget_failure_reason(input_route: list[object], output_route: list[object]) -> str | None:
    if input_route and not output_route:
        return "budget_fit_removed_all_points"
    if not input_route:
        return "no_route_before_budget_fit"
    return None


def _route_completeness(route: list[object], target: int) -> float:
    return round(len(route) / max(1, target), 3)


def _failure_stage(candidates: list[object], filtered: list[object], scored: list[object], route: list[object], budget_route: list[object], gate: object) -> str:
    if budget_route:
        return "none"
    if not candidates:
        return "retrieval"
    if not filtered:
        return "hard_filters"
    if not scored:
        return "scoring"
    if not route:
        return "assembly"
    if not budget_route:
        return "budget_fit"
    status = str(getattr(gate, "route_quality_status", "") or "")
    return "quality_gates" if status in {"failed", "algorithm_error"} else "none"


def _tail_location(route: list[object], ctx: object) -> tuple[float, float]:
    if route:
        last = route[-1]
        return float(getattr(last, "lat")), float(getattr(last, "lng"))
    return ctx.location


def _start_lat(ctx: object) -> float | None:
    lat, _lng = getattr(ctx, "location", (None, None))
    return float(lat) if isinstance(lat, (int, float)) else None


def _start_lng(ctx: object) -> float | None:
    _lat, lng = getattr(ctx, "location", (None, None))
    return float(lng) if isinstance(lng, (int, float)) else None


def _distance_meters_from_ctx(place: object, ctx: object) -> int | None:
    if place is None or getattr(place, "lat", None) is None or getattr(place, "lng", None) is None:
        return None
    lat, lng = getattr(ctx, "location", (None, None))
    if lat is None or lng is None:
        return None
    minutes = walk_minutes_between(float(lat), float(lng), float(place.lat), float(place.lng))
    return int(round(minutes * 80))


def _soft_budget_minutes(ctx: object) -> int:
    return int(_budget_minutes(ctx) * SOFT_BUDGET_FILL_RATIO)


def _hard_budget_minutes(ctx: object) -> int:
    return int(_budget_minutes(ctx) * HARD_BUDGET_FILL_RATIO)


def _budget_minutes(ctx: object) -> int:
    return int(getattr(ctx, "effective_time_budget_minutes", 0) or getattr(ctx, "time_budget_minutes", 0) or 0)


def _route_minutes(route: list[object]) -> int:
    return sum(_point_minutes(point) for point in route)


def _point_minutes(point: object) -> int:
    walk = int(getattr(point, "estimated_walk_minutes", 0) or 0)
    visit = int(getattr(point, "visit_minutes", 0) or 0)
    return max(0, walk + visit)


def _annotate_quality(place: object) -> object:
    place.validation = validate_place(place)
    return apply_runtime_place_defaults(place)


def _place_sample(places: list[object], ctx: object | None = None, limit: int = DEBUG_SAMPLE_LIMIT) -> list[dict[str, Any]]:
    return [_place_debug(place, ctx) for place in list(places or [])[:limit]]


def _place_debug(place: object, ctx: object | None = None) -> dict[str, Any]:
    result = {"id": str(getattr(place, "id", "") or ""), "title": _text(getattr(place, "title", None) or getattr(place, "name", None)), "category": _text(getattr(place, "category", None)), "lat": _rounded(getattr(place, "lat", None)), "lng": _rounded(getattr(place, "lng", None)), "status": _text(getattr(place, "status", None)), "lifecycle_status": _text(getattr(place, "lifecycle_status", None)), "is_route_eligible": getattr(place, "is_route_eligible", None), "is_published": getattr(place, "is_published", None), "is_visible_in_catalog": getattr(place, "is_visible_in_catalog", None), "price_level": getattr(place, "price_level", None), "quality_tier": _text(getattr(place, "quality_tier", None))}
    if ctx is not None and getattr(place, "lat", None) is not None and getattr(place, "lng", None) is not None:
        lat, lng = getattr(ctx, "location", (None, None))
        if lat is not None and lng is not None:
            result["walk_from_start_min"] = walk_minutes_between(float(lat), float(lng), float(place.lat), float(place.lng))
    validation = getattr(place, "validation", None)
    if isinstance(validation, dict):
        result["validation_issues"] = list(validation.get("issues", []) or [])[:8]
    return result


def _rejected_sample(rejected: list[object], ctx: object | None = None, limit: int = DEBUG_SAMPLE_LIMIT) -> list[dict[str, Any]]:
    sample = []
    for item in list(rejected or [])[:limit]:
        place = getattr(item, "place", item)
        row = _place_debug(place, ctx)
        for attr in ("reason", "reasons", "hard_reason", "budget_reason"):
            value = getattr(item, attr, None)
            if value:
                row[attr] = value
        sample.append(row)
    return sample


def _scored_sample(scored: list[object], ctx: object | None = None, limit: int = DEBUG_SAMPLE_LIMIT) -> list[dict[str, Any]]:
    result = []
    for item in list(scored or [])[:limit]:
        place = getattr(item, "place", None)
        row = _place_debug(place, ctx) if place is not None else {}
        row["score"] = round(float(getattr(item, "score", 0.0) or 0.0), 4)
        row["visit_minutes"] = visit_minutes_for_scored(item, ctx) if ctx is not None and place is not None else None
        row["breakdown"] = _safe_breakdown(getattr(item, "breakdown", None))
        result.append(row)
    return result


def _route_point_sample(route: list[object], limit: int = DEBUG_SAMPLE_LIMIT) -> list[dict[str, Any]]:
    result = []
    for point in list(route or [])[:limit]:
        result.append({"place_id": str(getattr(point, "place_id", "") or ""), "title": _text(getattr(point, "title", None)), "category": _text(getattr(point, "category", None)), "lat": _rounded(getattr(point, "lat", None)), "lng": _rounded(getattr(point, "lng", None)), "score": round(float(getattr(point, "score", 0.0) or 0.0), 4), "walk_minutes": int(getattr(point, "estimated_walk_minutes", 0) or 0), "visit_minutes": int(getattr(point, "visit_minutes", 0) or 0), "total_minutes": _point_minutes(point), "price_level": getattr(point, "price_level", None)})
    return result


def _first_point_fit_debug(scored: list[object], ctx: object, limit: int = DEBUG_SAMPLE_LIMIT) -> dict[str, Any]:
    budget = _budget_minutes(ctx)
    lat, lng = getattr(ctx, "location", (None, None))
    rows = []
    walk_values = []
    for item in list(scored or [])[: min(len(scored or []), 80)]:
        place = getattr(item, "place", None)
        if place is None or lat is None or lng is None:
            continue
        walk = walk_minutes_between(float(lat), float(lng), float(place.lat), float(place.lng))
        visit = visit_minutes_for_scored(item, ctx)
        total = walk + visit
        walk_values.append(walk)
        reasons = []
        if visit > budget:
            reasons.append("visit_gt_budget")
        if total > budget:
            reasons.append("walk_plus_visit_gt_budget")
        if walk > 45:
            reasons.append("walk_gt_45_strict")
        if walk > 90:
            reasons.append("walk_gt_90_relaxed")
        rows.append({"id": str(getattr(place, "id", "") or ""), "title": _text(getattr(place, "title", None) or getattr(place, "name", None)), "category": _text(getattr(place, "category", None)), "score": round(float(getattr(item, "score", 0.0) or 0.0), 4), "walk": walk, "visit": visit, "total": total, "fits_budget": total <= budget, "reject_reasons_if_first": reasons})
    rows.sort(key=lambda row: (row["walk"], -row["score"]))
    return {"budget": budget, "min_walk": min(walk_values) if walk_values else None, "max_walk_in_checked": max(walk_values) if walk_values else None, "checked_count": len(rows), "closest_candidates": rows[:limit], "top_score_candidates": sorted(rows, key=lambda row: -row["score"])[:limit]}


def _category_counts(items: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items or []:
        category = str(getattr(item, "category", "") or "unknown")
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:20])


def _scored_category_counts(scored: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in scored or []:
        place = getattr(item, "place", None)
        category = str(getattr(place, "category", "") or "unknown")
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:20])


def _validation_issue_counts(places: list[object]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for place in places or []:
        validation = getattr(place, "validation", None)
        if not isinstance(validation, dict):
            continue
        for issue in validation.get("issues", []) or []:
            key = str(issue)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda row: (-row[1], row[0]))[:30])


def _score_min(scored: list[object]) -> float | None:
    if not scored:
        return None
    return round(min(float(getattr(item, "score", 0.0) or 0.0) for item in scored), 4)


def _score_max(scored: list[object]) -> float | None:
    if not scored:
        return None
    return round(max(float(getattr(item, "score", 0.0) or 0.0) for item in scored), 4)


def _safe_breakdown(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): _debug_breakdown_value(raw) for key, raw in value.items()}


def _debug_breakdown_value(value: object) -> object:
    try:
        return round(float(value or 0.0), 4)
    except (TypeError, ValueError):
        return str(value)


def _rounded(value: object) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return None


def _text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None
