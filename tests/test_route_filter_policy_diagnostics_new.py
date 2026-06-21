from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_filter_policy import (
    DROP_BY_EXCLUSION,
    DROP_BY_STATUS,
    DROP_BY_TIME,
    filter_places,
)


def _ctx() -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id="diagnostic-test-city",
        timezone="UTC",
        time_budget_minutes=120,
        effective_time_budget_minutes=120,
        time_of_day=None,
        route_time_mode="now",
        interests=[],
        avoided_categories=["museums"],
        avoided_place_ids=["explicit"],
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


def _place(place_id: str, category: str, *, is_active: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id=place_id,
        lat=55.0,
        lng=20.0,
        category=category,
        price_level=1,
        is_active=is_active,
        status="active",
    )


def test_filter_report_exposes_diagnostic_drop_buckets_new() -> None:
    places = [
        _place("inactive", "cafe", is_active=False),
        _place("museum", "museum"),
        _place("explicit", "park"),
        _place("closed", "cafe"),
    ]

    def open_state(place: object, _now: datetime) -> str:
        return "closed" if getattr(place, "id", None) == "closed" else "open"

    report = filter_places(
        places,
        _ctx(),
        datetime(2030, 6, 3, 10, 0, 0),
        min_pool_size=99,
        open_state=open_state,
    )

    assert report.reason_counts[DROP_BY_STATUS] == 1
    assert report.reason_counts[DROP_BY_EXCLUSION] == 2
    assert report.reason_counts[DROP_BY_TIME] == 1
    assert report.reason_counts["status"] == 1
    assert report.reason_counts["avoided_category"] == 1
    assert report.reason_counts["explicit_place_exclude"] == 1
    assert report.reason_counts["closed_now"] == 1
