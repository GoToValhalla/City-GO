from __future__ import annotations

from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.candidate_retrieval_service import (
    LOCATION_FALLBACK_MAX_DISTANCE_METERS,
    CandidateRetrievalService,
)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


class _Db:
    def __init__(self, city: object) -> None:
        self.city = city

    def execute(self, _statement: object) -> _ScalarResult:
        return _ScalarResult(self.city)


def _ctx(location: tuple[float, float]) -> MergedContext:
    return MergedContext(
        location=location,
        city_id="khanty-mansiysk",
        timezone="Asia/Yekaterinburg",
        time_budget_minutes=240,
        effective_time_budget_minutes=240,
        time_of_day=None,
        route_time_mode="flexible",
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


def test_location_far_from_selected_city_falls_back_to_city_center_new() -> None:
    city = SimpleNamespace(center_lat=61.0042, center_lng=69.0019)
    ctx = _ctx((48.8566, 2.3522))

    CandidateRetrievalService()._apply_city_center_location_fallback(_Db(city), ctx)

    assert ctx.location == (61.0042, 69.0019)
    assert ctx.location_fallback_applied is True
    assert ctx.location_fallback_reason == "outside_selected_city"
    assert ctx.original_location == (48.8566, 2.3522)
    assert ctx.city_center_location == (61.0042, 69.0019)
    assert ctx.distance_to_city_center_meters is not None
    assert ctx.distance_to_city_center_meters > LOCATION_FALLBACK_MAX_DISTANCE_METERS


def test_location_near_selected_city_keeps_requested_start_new() -> None:
    city = SimpleNamespace(center_lat=61.0042, center_lng=69.0019)
    ctx = _ctx((61.01, 69.01))

    CandidateRetrievalService()._apply_city_center_location_fallback(_Db(city), ctx)

    assert ctx.location == (61.01, 69.01)
    assert ctx.location_fallback_applied is False
    assert ctx.location_fallback_reason is None
    assert ctx.original_location is None
    assert ctx.city_center_location == (61.0042, 69.0019)
    assert ctx.distance_to_city_center_meters is not None
    assert ctx.distance_to_city_center_meters <= LOCATION_FALLBACK_MAX_DISTANCE_METERS
