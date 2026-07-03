from __future__ import annotations

from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_optimizer import STRICT_MAX_WALK_MINUTES, assemble_route
from services.route_assembly_service import RoutePoint
from services.scoring_service import ScoredPlace


def _ctx(*, budget: int = 240) -> MergedContext:
    return MergedContext(
        location=(0.0, 0.0),
        city_id="low-density-test-city",
        time_budget_minutes=budget,
        effective_time_budget_minutes=budget,
        time_of_day=None,
        route_time_mode="flexible",
        require_known_hours=False,
        interests=[],
        interest_removed_due_to_avoidance=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=6500,
        effective_num_stops=6,
        min_stop_duration_minutes=20,
    )


def _place(idx: int, lat: float, lng: float, category: str = "museum") -> SimpleNamespace:
    return SimpleNamespace(
        id=idx,
        title=f"Place {idx}",
        address=f"Address {idx}",
        public_image_url=None,
        image_url=None,
        short_description=None,
        source="test",
        city=None,
        lat=lat,
        lng=lng,
        category=category,
        average_visit_duration_minutes=20,
        effective_visit_duration_minutes=20,
        opening_hours=None,
        effective_opening_hours=None,
        price_level=1,
        validation={"issues": []},
    )


def _scored(idx: int, lat: float, lng: float, score: float = 0.9, category: str = "museum") -> ScoredPlace:
    return ScoredPlace(
        _place(idx, lat, lng, category),
        score,
        {"interest": 0.5},
    )


def _route_minutes(route: list[object]) -> int:
    return sum(
        int(getattr(point, "visit_minutes", 0) or 0)
        + int(getattr(point, "estimated_walk_minutes", 0) or 0)
        for point in route
    )


def test_assembly_first_point_walk_cap_amnesty_keeps_far_seed_new() -> None:
    route = assemble_route(
        [_scored(1, 0.04, 0.0)],
        _ctx(budget=240),
        RoutePoint,
    )

    assert len(route) == 1
    assert route[0].place_id == "1"
    assert route[0].estimated_walk_minutes > STRICT_MAX_WALK_MINUTES


def test_assembly_sparse_graph_respects_budget_instead_of_forcing_mvp_new() -> None:
    budget = 120
    route = assemble_route(
        [
            _scored(1, 0.04, 0.0, score=0.95, category="museum"),
            _scored(2, -0.04, 0.0, score=0.94, category="park"),
            _scored(3, 0.0, 0.06, score=0.93, category="viewpoint"),
        ],
        _ctx(budget=budget),
        RoutePoint,
    )

    assert len(route) == 1
    assert route[0].place_id == "1"
    assert _route_minutes(route) <= budget
