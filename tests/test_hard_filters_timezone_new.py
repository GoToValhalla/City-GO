from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.hard_filters_service import HardFiltersService


def _ctx(timezone: str = "UTC") -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id="timezone-test-city",
        timezone=timezone,
        time_budget_minutes=120,
        effective_time_budget_minutes=120,
        time_of_day=None,
        route_time_mode="now",
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
        radius_meters=1500,
        effective_num_stops=4,
        min_stop_duration_minutes=20,
    )


def _place(idx: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=idx,
        lat=55.0,
        lng=20.0,
        category="cafe",
        price_level=1,
        is_active=True,
        status="active",
        opening_hours={"mon": {"open": "09:00", "close": "21:00"}},
    )


def test_hard_filters_check_now_in_city_timezone_new() -> None:
    # Monday 04:00 UTC is Monday 09:00 in Asia/Yekaterinburg.
    # Without city-timezone conversion, all places would look closed at 04:00.
    report = HardFiltersService().apply_with_report(
        [_place(idx) for idx in range(16)],
        _ctx("Asia/Yekaterinburg"),
        datetime(2030, 6, 3, 4, 0, 0),
    )

    assert report.strict_kept_count == 16
    assert report.reason_counts == {}
