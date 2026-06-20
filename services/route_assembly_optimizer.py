from __future__ import annotations

from dataclasses import dataclass

from schemas.merged_context import MergedContext
from services.route_adaptive_plan import adaptive_target_points
from services.route_diversity_policy import add_category, can_use_category, normalize_category
from services.route_geometry import walk_minutes_between
from services.route_point_factory import route_point_from_scored, visit_minutes_for_scored
from services.route_walk_annotations import annotate_walks
from services.scoring_service import ScoredPlace

MIN_BUDGET_UTILIZATION = 0.65
TARGET_BUDGET_UTILIZATION = 0.86
DEFAULT_MINUTES_PER_POINT = 30
DEFAULT_ASSEMBLY_BUDGET_MINUTES = 240
MAX_TARGET_POINTS = 8
MAX_RELAXATION_STAGE = 3
STRICT_MAX_WALK_MINUTES = 45
RELAXED_MAX_WALK_MINUTES = 90
MAX_CANDIDATE_POOL = 500
WALK_INTERESTS = {"walk", "park", "outdoor", "sea"}
WALK_ROUTE_CATEGORIES = {
    "walk", "park", "outdoor", "attraction", "culture", "coffee", "cafe",
    "museum", "gallery", "historic", "history", "landmark", "monument",
    "promenade", "sightseeing", "viewpoint", "food", "restaurant",
}


@dataclass(frozen=True)
class AssemblyState:
    route: list[object]
    remaining: int
    lat: float
    lng: float
    used_categories: dict[str, int]
    candidates: list[ScoredPlace]
    target_points: int
    relaxed_budget: bool = False
    relaxation_stage: int = 0


def assemble_route(scored: list[ScoredPlace], ctx: MergedContext, point_cls: type) -> list[object]:
    if not scored:
        return []

    lat, lng = ctx.location
    budget = _assembly_budget(ctx)
    target_points = _target_points(ctx, budget, scored)
    candidate_pool = scored[:MAX_CANDIDATE_POOL]

    seed = _anchor_seed(candidate_pool, ctx, point_cls)
    remaining_pool = [item for item in candidate_pool if str(getattr(item.place, "id", "")) not in _route_ids(seed)]
    state = _initial_state(seed, budget, lat, lng, remaining_pool, target_points)
    route = _select_until_done(state, ctx, point_cls)

    # If the normal optimizer cannot pick the first point, do not return no_route for
    # a city that has scored candidates. The first leg may be far from ctx.location
    # because the UI start point can be city center / hotel / arbitrary map point.
    if not route:
        route = _first_point_seed_fallback(candidate_pool, ctx, point_cls, budget)

    if _needs_time_fill(route, budget, target_points):
        route = _fill_remaining_time(route, candidate_pool, ctx, point_cls, budget, target_points)

    if _needs_time_fill(route, budget, target_points):
        route = _greedy_proximity_backfill(route, candidate_pool, ctx, point_cls, budget, target_points)

    # Final product-safety fallback: for cities with many valid candidates the assembly
    # should try to reach the minimum useful 3-point route. The budget guard still wins,
    # so genuinely short routes become partial instead of fake-ready.
    if _needs_minimum_point_backfill(route, candidate_pool, target_points):
        route = _minimum_point_backfill(route, candidate_pool, ctx, point_cls, budget, target_points)

    return annotate_walks(_cleanup_loops(route), ctx.location)


def _select_until_done(state: AssemblyState, ctx: MergedContext, point_cls: type) -> list[object]:
    if _done(state, ctx):
        return state.route

    selected = _best_candidate(state, ctx)
    if selected is None:
        relaxed = _relax_state(state, ctx)
        if relaxed is None:
            return state.route
        selected = _best_candidate(relaxed, ctx)
        if selected is None:
            return state.route
        state = relaxed

    point = route_point_from_scored(selected, ctx, point_cls)
    walk = walk_minutes_between(state.lat, state.lng, point.lat, point.lng)
    point.estimated_walk_minutes = walk
    return _select_until_done(_next_state(state, selected, point, walk), ctx, point_cls)


def _anchor_seed(scored: list[ScoredPlace], ctx: MergedContext, point_cls: type) -> list[object]:
    anchors = [item for item in scored if float(item.breakdown.get("route_anchor", 0.0) or 0.0) >= 1.0]
    if len(anchors) != 1:
        return []
    lat, lng = ctx.location
    point = route_point_from_scored(anchors[0], ctx, point_cls)
    point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
    return [point]


def _initial_state(
    seed: list[object], budget: int, lat: float, lng: float, candidates: list[ScoredPlace], target_points: int
) -> AssemblyState:
    if not seed:
        return AssemblyState([], budget, lat, lng, {}, candidates, target_points)
    point = seed[-1]
    used = {normalize_category(getattr(point, "category", "")): 1}
    spent = _route_minutes(seed)
    return AssemblyState(seed, max(0, budget - spent), float(point.lat), float(point.lng), used, candidates, target_points)


def _route_ids(route: list[object]) -> set[str]:
    return {str(getattr(point, "place_id", "")) for point in route}


def _done(state: AssemblyState, ctx: MergedContext) -> bool:
    return len(state.route) >= state.target_points or state.remaining <= ctx.min_stop_duration_minutes


def _best_candidate(state: AssemblyState, ctx: MergedContext) -> ScoredPlace | None:
    feasible = tuple(filter(lambda item: _fits(item, state, ctx), state.candidates))
    return max(feasible, key=lambda item: _assembly_score(item, state, ctx), default=None)


def _fits(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> bool:
    category = str(getattr(scored.place, "category", "") or "")
    if not _can_use_category_for_route(category, state.used_categories, state.relaxation_stage, len(state.route), ctx):
        return False
    if _total_minutes(scored, state, ctx) > state.remaining:
        return False
    walk = walk_minutes_between(state.lat, state.lng, float(scored.place.lat), float(scored.place.lng))
    # The first leg must not be allowed to kill the whole route. For the first point
    # the user may start outside the dense POI cluster, while later legs still need
    # walk caps to keep the route sane.
    if not state.route:
        return True
    return walk <= _max_walk_minutes_for_stage(state.relaxation_stage)


def _can_use_category_for_route(category: str, used: dict[str, int], relaxation_stage: int, route_len: int, ctx: MergedContext) -> bool:
    normalized = normalize_category(category)
    if not normalized:
        return can_use_category(category, used)

    if relaxation_stage <= 0:
        if _is_walking_route(ctx) and normalized in WALK_ROUTE_CATEGORIES:
            return used.get(normalized, 0) < 3
        return can_use_category(category, used)

    if route_len >= 2 and relaxation_stage < MAX_RELAXATION_STAGE:
        return _can_use_category_for_route(category, used, 0, route_len, ctx)

    base_limit = 5 if (_is_walking_route(ctx) and normalized in WALK_ROUTE_CATEGORIES) else 3
    return used.get(normalized, 0) < base_limit + relaxation_stage


def _relax_state(state: AssemblyState, ctx: MergedContext) -> AssemblyState | None:
    underfilled = len(state.route) < min(3, state.target_points)
    if underfilled and state.relaxation_stage < MAX_RELAXATION_STAGE:
        return AssemblyState(state.route, state.remaining, state.lat, state.lng, state.used_categories, state.candidates, state.target_points, state.relaxed_budget, state.relaxation_stage + 1)

    if not state.relaxed_budget and len(state.route) == 0:
        extra = _assembly_budget(ctx)
        return AssemblyState(state.route, max(state.remaining, int(extra * 1.1)), state.lat, state.lng, state.used_categories, state.candidates, state.target_points, True, min(MAX_RELAXATION_STAGE, state.relaxation_stage + 1))

    return None


def _total_minutes(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> int:
    place = scored.place
    walk = walk_minutes_between(state.lat, state.lng, float(place.lat), float(place.lng))
    return walk + visit_minutes_for_scored(scored, ctx)


def _assembly_score(scored: ScoredPlace, state: AssemblyState, ctx: MergedContext) -> float:
    total = max(1, _total_minutes(scored, state, ctx))
    value_per_minute = float(scored.score) / total
    interest = float(scored.breakdown.get("interest", 0.0)) if isinstance(scored.breakdown, dict) else 0.0
    route_fit = _walk_route_fit(scored, ctx)
    diversity_penalty = _category_pressure(scored, state)
    proximity_bonus = _proximity_bonus(scored, state)
    return float(scored.score) * 0.42 + min(1.0, value_per_minute * 24.0) * 0.24 + interest * 0.12 + route_fit * 0.10 + proximity_bonus * 0.18 - diversity_penalty


def _proximity_bonus(scored: ScoredPlace, state: AssemblyState) -> float:
    walk = walk_minutes_between(state.lat, state.lng, float(scored.place.lat), float(scored.place.lng))
    if walk <= 8:
        return 1.0
    if walk <= 18:
        return 0.75
    if walk <= 30:
        return 0.45
    if walk <= 45:
        return 0.22
    return 0.0


def _category_pressure(scored: ScoredPlace, state: AssemblyState) -> float:
    category = normalize_category(getattr(scored.place, "category", ""))
    if not category:
        return 0.0
    return min(0.18, state.used_categories.get(category, 0) * 0.04)


def _next_state(state: AssemblyState, selected: ScoredPlace, point: object, walk: int) -> AssemblyState:
    left = [item for item in state.candidates if item is not selected]
    spent = walk + int(getattr(point, "visit_minutes", 0) or 0)
    used = add_category(str(getattr(point, "category", "") or ""), state.used_categories)
    return AssemblyState([*state.route, point], state.remaining - spent, point.lat, point.lng, used, left, state.target_points, state.relaxed_budget, state.relaxation_stage)


def _needs_time_fill(route: list[object], budget: int, target_points: int) -> bool:
    if not route:
        return False
    if len(route) < min(2, target_points):
        return True
    return len(route) < target_points and _route_minutes(route) < int(budget * MIN_BUDGET_UTILIZATION)


def _fill_remaining_time(route: list[object], scored: list[ScoredPlace], ctx: MergedContext, point_cls: type, budget: int, target_points: int) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    used_categories: dict[str, int] = {}
    for point in current:
        used_categories = add_category(str(getattr(point, "category", "") or ""), used_categories)

    while len(current) < target_points and _route_minutes(current) < int(budget * TARGET_BUDGET_UTILIZATION):
        lat, lng = _tail_location(current, ctx)
        remaining = budget - _route_minutes(current)
        if remaining <= ctx.min_stop_duration_minutes:
            break
        candidates = [item for item in scored if str(getattr(item.place, "id", "")) not in used_ids]
        stage = _fill_stage(current, budget)
        state = AssemblyState(current, remaining, lat, lng, used_categories, candidates, target_points, relaxation_stage=stage)
        selected = _best_candidate(state, ctx)
        if selected is None:
            break
        point = route_point_from_scored(selected, ctx, point_cls)
        point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
        current.append(point)
        used_ids.add(str(getattr(point, "place_id", "")))
        used_categories = add_category(str(getattr(point, "category", "") or ""), used_categories)
    return current


def _greedy_proximity_backfill(route: list[object], scored: list[ScoredPlace], ctx: MergedContext, point_cls: type, budget: int, target_points: int) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    min_points = min(3, target_points, len(scored))

    while len(current) < target_points and _route_minutes(current) < int(budget * TARGET_BUDGET_UTILIZATION):
        lat, lng = _tail_location(current, ctx)
        remaining = budget - _route_minutes(current)
        if remaining <= ctx.min_stop_duration_minutes:
            break
        candidates = [item for item in scored if str(getattr(item.place, "id", "")) not in used_ids]
        selected = _nearest_feasible_candidate(candidates, lat, lng, remaining, ctx, require_close=len(current) >= min_points)
        if selected is None:
            break
        point = route_point_from_scored(selected, ctx, point_cls)
        point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
        current.append(point)
        used_ids.add(str(getattr(point, "place_id", "")))
    return current


def _nearest_feasible_candidate(candidates: list[ScoredPlace], lat: float, lng: float, remaining: int, ctx: MergedContext, require_close: bool) -> ScoredPlace | None:
    feasible = []
    for item in candidates:
        walk = walk_minutes_between(lat, lng, float(item.place.lat), float(item.place.lng))
        total = walk + visit_minutes_for_scored(item, ctx)
        max_walk = STRICT_MAX_WALK_MINUTES if require_close else RELAXED_MAX_WALK_MINUTES
        if total <= remaining and walk <= max_walk:
            feasible.append((walk, -float(item.score), item))
    feasible.sort(key=lambda item: (item[0], item[1]))
    return feasible[0][2] if feasible else None


def _first_point_seed_fallback(scored: list[ScoredPlace], ctx: MergedContext, point_cls: type, budget: int) -> list[object]:
    lat, lng = ctx.location
    feasible = []
    for item in scored:
        visit = visit_minutes_for_scored(item, ctx)
        if visit > budget:
            continue
        walk = walk_minutes_between(lat, lng, float(item.place.lat), float(item.place.lng))
        # Order by quality first, but keep the seed reasonably close when possible.
        feasible.append((-float(item.score), walk, visit, item))
    feasible.sort(key=lambda row: (row[0], row[1], row[2]))
    if not feasible:
        return []
    item = feasible[0][3]
    point = route_point_from_scored(item, ctx, point_cls)
    point.estimated_walk_minutes = walk_minutes_between(lat, lng, point.lat, point.lng)
    return [point]


def _needs_minimum_point_backfill(route: list[object], scored: list[ScoredPlace], target_points: int) -> bool:
    return bool(scored) and len(route) < _minimum_fallback_points(scored, target_points)


def _minimum_point_backfill(route: list[object], scored: list[ScoredPlace], ctx: MergedContext, point_cls: type, budget: int, target_points: int) -> list[object]:
    current = list(route)
    used_ids = {str(getattr(point, "place_id", "")) for point in current}
    min_points = _minimum_fallback_points(scored, target_points)

    for item in scored:
        if len(current) >= min_points:
            break
        place_id = str(getattr(item.place, "id", ""))
        if not place_id or place_id in used_ids:
            continue
        tail_lat, tail_lng = _tail_location(current, ctx)
        visit = visit_minutes_for_scored(item, ctx)
        walk = walk_minutes_between(tail_lat, tail_lng, float(item.place.lat), float(item.place.lng))
        if _route_minutes(current) + walk + visit > budget:
            continue
        point = route_point_from_scored(item, ctx, point_cls)
        point.estimated_walk_minutes = walk
        current.append(point)
        used_ids.add(place_id)

    return current


def _minimum_fallback_points(scored: list[ScoredPlace], target_points: int) -> int:
    return min(3, max(1, target_points), len(scored))


def _fill_stage(route: list[object], budget: int) -> int:
    if len(route) < 2:
        return MAX_RELAXATION_STAGE
    return 1


def _tail_location(route: list[object], ctx: MergedContext) -> tuple[float, float]:
    if route:
        last = route[-1]
        return float(getattr(last, "lat")), float(getattr(last, "lng"))
    return ctx.location


def _route_minutes(route: list[object]) -> int:
    return sum(int(getattr(point, "visit_minutes", 0) or 0) + int(getattr(point, "estimated_walk_minutes", 0) or 0) for point in route)


def _target_points(ctx: MergedContext, budget: int, scored: list[ScoredPlace]) -> int:
    target = adaptive_target_points(scored, ctx)
    return min(MAX_TARGET_POINTS, max(1, target or 1))


def _is_walking_route(ctx: MergedContext) -> bool:
    interests = {str(item).strip().casefold() for item in getattr(ctx, "interests", []) or []}
    return bool(interests & WALK_INTERESTS)


def _walk_route_fit(scored: ScoredPlace, ctx: MergedContext) -> float:
    category = str(getattr(scored.place, "category", "") or "").strip().casefold()
    return 1.0 if _is_walking_route(ctx) and category in WALK_ROUTE_CATEGORIES else 0.0


def _cleanup_loops(route: list[object]) -> list[object]:
    if len(route) < 3:
        return route
    first, second, third, *tail = route
    return _cleanup_loops([first, third, second, *tail]) if _swap_shortens(first, second, third) else [first, *_cleanup_loops([second, third, *tail])]


def _swap_shortens(first: object, second: object, third: object) -> bool:
    current = walk_minutes_between(first.lat, first.lng, second.lat, second.lng)
    swapped = walk_minutes_between(first.lat, first.lng, third.lat, third.lng)
    return swapped < current


def _assembly_budget(ctx: MergedContext) -> int:
    effective = int(getattr(ctx, "effective_time_budget_minutes", 0) or 0)
    explicit = int(getattr(ctx, "time_budget_minutes", 0) or 0)
    budget = effective or explicit
    return budget if budget > 0 else DEFAULT_ASSEMBLY_BUDGET_MINUTES


def _max_walk_minutes_for_stage(stage: int) -> int:
    if stage <= 0:
        return STRICT_MAX_WALK_MINUTES
    if stage >= MAX_RELAXATION_STAGE:
        return RELAXED_MAX_WALK_MINUTES
    return STRICT_MAX_WALK_MINUTES + (stage * 12)
