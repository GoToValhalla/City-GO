from datetime import datetime
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.hard_filters_service import HardFiltersService


def _ctx(**overrides) -> MergedContext:
    data = {
        "location": (55.0, 20.0),
        "city_id": "test-city",
        "time_budget_minutes": 120,
        "effective_time_budget_minutes": 120,
        "interests": ["coffee"],
        "avoided_categories": ["coffee"],
        "avoided_place_ids": [],
        "budget_level": BudgetLevel.MID,
        "pace_mode": PaceMode.NORMAL,
        "pace_multiplier": 1.0,
        "local_vs_tourist": 0.5,
        "novelty_mode": False,
        "is_visiting": False,
        "visit_city_id": None,
        "visit_days": 1,
        "radius_meters": 5000,
        "effective_num_stops": 4,
        "min_stop_duration_minutes": 20,
    }
    data.update(overrides)
    return MergedContext(**data)


def _place(pid: int, category: str) -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        lat=55.0,
        lng=20.0,
        category=category,
        price_level=1,
        status="active",
        is_active=True,
        lifecycle_status=None,
        deleted_at=None,
        is_route_eligible=True,
        opening_hours=None,
    )


def test_avoided_category_excludes_most_places_but_never_violates_constraint() -> None:
    places = [_place(index, "coffee") for index in range(20)] + [_place(99, "museum")]
    report = HardFiltersService().apply_with_report(places, _ctx(), datetime(2030, 1, 1, 12))
    assert [place.id for place in report.kept] == [99]
    assert report.reason_counts["avoided_category"] == 20
