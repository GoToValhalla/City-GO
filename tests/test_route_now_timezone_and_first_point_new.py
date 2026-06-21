from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.hard_filters_service import HardFiltersService
from services.route_assembly_optimizer import assemble_route
from services.route_assembly_service import RoutePoint
from services.scoring_service import ScoredPlace
from services.time_aware_service import TimeAwareService


def _ctx(*, route_time_mode: str = "now", timezone: str = "Asia/Yekaterinburg") -> MergedContext:
    return MergedContext(
        location=(61.0, 69.0),
        city_id="khanty-mansiysk",
        timezone=timezone,
        time_budget_minutes=240,
        effective_time_budget_minutes=240,
        time_of_day=None,
        route_time_mode=route_time_mode,
        interests=[],
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


def _opening(open_time: str, close_time: str) -> dict[str, dict[str, str]]:
    return {day: {"open": open_time, "close": close_time} for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")}


def _place(place_id: str, lat: float, lng: float, *, opening_hours: dict[str, dict[str, str]] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        id=place_id,
        title=f"Place {place_id}",
        lat=lat,
        lng=lng,
        category="museum",
        price_level=1,
        average_visit_duration_minutes=30,
        opening_hours=opening_hours or _opening("10:00", "18:00"),
        is_active=True,
        status="active",
        is_published=True,
        is_route_eligible=True,
        is_visible_in_catalog=True,
    )


def test_now_mode_uses_city_timezone_for_hard_filters_new() -> None:
    ctx = _ctx(timezone="Asia/Yekaterinburg")
    # 07:00 UTC is 12:00 in Khanty-Mansiysk/Yekaterinburg time.
    # If the filter treats this naive datetime as local wall time, the place is closed.
    now_utc_naive = datetime(2030, 6, 3, 7, 0, 0)
    place = _place("open-local-noon", 61.001, 69.001, opening_hours=_opening("10:00", "18:00"))

    kept = HardFiltersService().apply([place], ctx, now_utc_naive)

    assert [item.id for item in kept] == ["open-local-noon"]


def test_time_aware_marks_closed_points_without_dropping_route_new() -> None:
    ctx = _ctx(timezone="Asia/Yekaterinburg")
    point = RoutePoint(
        place_id="closed-at-arrival",
        lat=61.001,
        lng=69.001,
        score=0.9,
        category="museum",
        visit_minutes=30,
        opening_hours=_opening("20:00", "21:00"),
    )

    route = TimeAwareService().apply([point], ctx, datetime(2030, 6, 3, 7, 0, 0))

    assert len(route) == 1
    assert route[0].time_status == "closed_at_arrival"
    assert route[0].is_valid is True


def test_assembly_allows_far_first_point_as_partial_seed_new() -> None:
    ctx = _ctx(route_time_mode="flexible")
    far_first_place = _place("far-first", 61.03, 69.0)
    scored = [ScoredPlace(far_first_place, 0.95, {"interest": 1.0})]

    route = assemble_route(scored, ctx, RoutePoint)

    assert len(route) == 1
    assert route[0].place_id == "far-first"
    assert route[0].estimated_walk_minutes > 45
