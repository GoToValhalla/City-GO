from __future__ import annotations

from datetime import datetime
from time import perf_counter

from sqlalchemy.orm import Session

from schemas.user_profile import UserProfile
from services.context_merge_service import RequestContext
from services.place_validation_service import validate_place
from services.route_pipeline_trace import RoutePipelineTrace, log_route_trace, timed_trace, top_scores
from services.route_pipeline_warnings import assembly_warnings, candidate_warnings, filter_warnings
from services.place_runtime_defaults import apply_runtime_place_defaults
from services.route_quality_warnings import route_quality_warnings
from services.route_start_time import effective_route_start
from models.city import City
from services.route_candidate_diagnostics import candidate_diagnostics
from services.route_diversity_policy import add_category, can_use_category, normalize_category
from services.route_generation_diagnostics.record import record_canonical_generation
from services.route_geometry import walk_minutes_between
from services.route_point_factory import route_point_from_scored, visit_minutes_for_scored
from services.route_assembly_service import RoutePoint
from services.route_quality_score import minimum_points_for_budget

MAX_CANDIDATE_OPTIONS = 40
SOFT_BUDGET_FILL_RATIO = 0.9
HARD_BUDGET_FILL_RATIO = 1.0
ROUTE_FRIENDLY_FILL_CATEGORIES = {"walk", "park", "outdoor", "attraction", "culture", "coffee", "cafe", "museum", "gallery"}
EMERGENCY_ROUTE_WARNING = "Emergency route fallback was used because standard route assembly returned zero points."


def build_dynamic_route(
    deps: object,
    db: Session,
    request: RequestContext,
    profile: UserProfile | None,
) -> object:
    trace = RoutePipelineTrace()
    ctx = _ctx(deps, request, profile, trace)
    now = effective_route_start(datetime.utcnow(), getattr(ctx, "time_of_day", None))
    candidates, input_warnings = _candidates(deps, db, ctx, trace)
    filtered, filtered_warnings = _filtered(deps, candidates, ctx, now, trace)
    scored = _scored(deps, filtered, ctx, trace)
    route, route_warnings = _route(deps, scored, filtered, ctx, now, trace)
    budget_fit = _budget_fit(deps, route, scored, ctx, trace)
    warnings = [*input_warnings, *filtered_warnings, *route_warnings,
                *route_quality_warnings(budget_fit.route, ctx.effective_num_stops),
                *budget_fit.warnings]
    final_route = deps.finalize.finalize(budget_fit.route, ctx, extra_warnings=warnings)
    final_route.pipeline_trace = trace.snapshot()
    final_route.candidate_options = _candidate_options(scored, ctx, budget_fit.route)
    final_route.generation_run_id = _record_generation(db, ctx, request, final_route)
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
    return record_canonical_generation(
        db, city=city, ctx=ctx, request_payload=payload, final_route=final_route,
    )


def _ctx(deps: object, request: RequestContext, profile: UserProfile | None, trace: RoutePipelineTrace):
    started = perf_counter()
    ctx = deps.context_merge.merge(request, profile)
    timed_trace(trace, "context_merge", started, interests=list(ctx.interests))
    return ctx


def _candidates(deps: object, db: Session, ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    candidates = deps.retrieval.get_candidates(db, ctx)
    timed_trace(trace, "candidate_retrieval", started, count=len(candidates),
                **candidate_diagnostics(db, ctx))
    started = perf_counter()
    annotated = list(map(_annotate_quality, candidates))
    warnings = candidate_warnings(annotated)
    timed_trace(trace, "quality_annotation", started, warning_count=len(warnings))
    return annotated, warnings


def _filtered(deps: object, candidates: list[object], ctx: object, now: datetime, trace: RoutePipelineTrace):
    started = perf_counter()
    report = deps.filters.apply_with_report(candidates, ctx, now)
    warnings = filter_warnings(candidates, report.kept)
    kept = report.kept
    emergency_filter_fallback = False
    if not kept and len(candidates) >= minimum_points_for_budget(_budget_minutes(ctx)):
        kept = candidates[: min(len(candidates), 300)]
        emergency_filter_fallback = True
        warnings = [*warnings, EMERGENCY_ROUTE_WARNING]
    timed_trace(trace, "hard_filter", started, input_count=len(candidates),
                kept_count=len(kept), original_kept_count=len(report.kept), removed_count=len(report.rejected),
                fallback_used=report.fallback_used, emergency_filter_fallback=emergency_filter_fallback,
                reasons=report.reason_counts)
    return kept, warnings


def _scored(deps: object, filtered: list[object], ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    scored = deps.scoring.score(filtered, ctx)
    timed_trace(trace, "scoring", started, count=len(scored), top3_scores=top_scores(scored))
    return scored


def _route(deps: object, scored: list[object], filtered: list[object], ctx: object,
           now: datetime, trace: RoutePipelineTrace):
    started = perf_counter()
    route = deps.assembly.build(scored, ctx)
    warnings = assembly_warnings(filtered, route)
    emergency_assembly_fallback = False
    original_selected_count = len(route)
    if not route and scored:
        route = _emergency_route_from_scored(scored, ctx)
        emergency_assembly_fallback = bool(route)
        if emergency_assembly_fallback:
            warnings = [*warnings, EMERGENCY_ROUTE_WARNING]
    timed_trace(trace, "assembly", started, selected_count=len(route), original_selected_count=original_selected_count,
                warning_count=len(warnings), emergency_assembly_fallback=emergency_assembly_fallback,
                route_minutes=_route_minutes(route))
    route = deps.time_ordering.order(route, ctx, now)
    route = deps.time.apply(route, ctx, now)
    timed_trace(trace, "time_aware", started, count=len(route), route_minutes=_route_minutes(route))
    return route, warnings


def _budget_fit(deps: object, route: list[object], scored: list[object], ctx: object, trace: RoutePipelineTrace):
    started = perf_counter()
    first_fit = deps.budget_fit.fit(route, ctx)
    filled_route = _fill_budget_gap(first_fit.route, scored, ctx)
    final_fit = deps.budget_fit.fit(filled_route, ctx)
    timed_trace(trace, "budget_fit", started,
                kept_count=len(final_fit.route),
                warning_count=len(final_fit.warnings),
                before_fit_input_count=len(route),
                before_fill_count=len(first_fit.route),
                after_fill_count=len(filled_route),
                route_minutes=_route_minutes(final_fit.route),
                target_minutes=_soft_budget_minutes(ctx),
                hard_budget_minutes=_hard_budget_minutes(ctx))
    return final_fit


def _emergency_route_from_scored(scored: list[object], ctx: object) -> list[RoutePoint]:
    budget = _hard_budget_minutes(ctx)
    min_points = minimum_points_for_budget(_budget_minutes(ctx))
    target_points = max(min_points, min(8, int(getattr(ctx, "effective_num_stops", 0) or min_points)))
    current: list[RoutePoint] = []
    used_ids: set[str] = set()
    remaining = list(scored[:300])

    while remaining and len(current) < target_points and _route_minutes(current) < budget:
        tail_lat, tail_lng = _tail_location(current, ctx)
        selected = _nearest_emergency_candidate(remaining, tail_lat, tail_lng, ctx, budget - _route_minutes(current))
        if selected is None:
            break
        point = route_point_from_scored(selected, ctx, RoutePoint)
        point.estimated_walk_minutes = walk_minutes_between(tail_lat, tail_lng, point.lat, point.lng)
        if _route_minutes(current) + _point_minutes(point) > budget and len(current) >= min_points:
            break
        current.append(point)
        used_ids.add(str(point.place_id))
        remaining = [item for item in remaining if str(getattr(item.place, "id", "")) not in used_ids]

    return current


def _nearest_emergency_candidate(scored: list[object], lat: float, lng: float, ctx: object, remaining_minutes: int) -> object | None:
    feasible = []
    for item in scored:
        place = item.place
        walk = walk_minutes_between(lat, lng, float(place.lat), float(place.lng))
        visit = visit_minutes_for_scored(item, ctx)
        total = walk + visit
        if total <= remaining_minutes or remaining_minutes >= int(getattr(ctx, "min_stop_duration_minutes", 20) or 20):
            feasible.append((walk, -float(getattr(item, "score", 0.0) or 0.0), total, item))
    feasible.sort(key=lambda row: (row[0], row[1], row[2]))
    return feasible[0][3] if feasible else None


def _fill_budget_gap(route: list[object], scored: list[object], ctx: object) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    used_categories = _used_categories(current)

    for item in scored:
        if _route_minutes(current) >= _soft_budget_minutes(ctx):
            break
        place_id = str(getattr(item.place, "id", ""))
        if not place_id or place_id in used_ids:
            continue
        category = normalize_category(getattr(item.place, "category", ""))
        if not _can_fill_category(category, used_categories, len(current), ctx):
            continue
        point = route_point_from_scored(item, ctx, RoutePoint)
        tail_lat, tail_lng = _tail_location(current, ctx)
        point.estimated_walk_minutes = walk_minutes_between(tail_lat, tail_lng, point.lat, point.lng)
        next_minutes = _route_minutes(current) + _point_minutes(point)
        if next_minutes > _hard_budget_minutes(ctx):
            continue
        current.append(point)
        used_ids.add(place_id)
        used_categories = add_category(category, used_categories)

    return current


def _can_fill_category(category: str, used_categories: dict[str, int], route_len: int, ctx: object) -> bool:
    if can_use_category(category, used_categories):
        return True
    min_points = minimum_points_for_budget(_budget_minutes(ctx))
    if route_len >= min_points:
        return False
    if category in ROUTE_FRIENDLY_FILL_CATEGORIES:
        return used_categories.get(category, 0) < 3
    return False


def _candidate_options(scored: list[object], ctx: object, route: list[object]) -> list[RoutePoint]:
    selected_ids = {str(getattr(point, "place_id", "")) for point in route}
    options = []
    for item in scored:
        point = route_point_from_scored(item, ctx, RoutePoint)
        if str(point.place_id) not in selected_ids:
            options.append(point)
        if len(options) >= MAX_CANDIDATE_OPTIONS:
            break
    return options


def _used_categories(route: list[object]) -> dict[str, int]:
    result: dict[str, int] = {}
    for point in route:
        result = add_category(str(getattr(point, "category", "") or ""), result)
    return result


def _tail_location(route: list[object], ctx: object) -> tuple[float, float]:
    if route:
        last = route[-1]
        return float(getattr(last, "lat")), float(getattr(last, "lng"))
    return ctx.location


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
