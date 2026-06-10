from datetime import datetime
from types import SimpleNamespace

from services.place_runtime_defaults import apply_runtime_place_defaults
from services.route_start_time import effective_route_start


def test_runtime_defaults_do_not_mutate_persistent_fields() -> None:
    place = SimpleNamespace(
        category="cafe",
        opening_hours=None,
        average_visit_duration_minutes=None,
    )

    result = apply_runtime_place_defaults(place)

    assert result.opening_hours is None
    assert result.average_visit_duration_minutes is None
    assert result.opening_hours_mode == "estimated_default"
    assert result.effective_visit_duration_minutes == 20
    assert result.effective_opening_hours["mon"] == {"open": "08:00", "close": "21:00"}


def test_effective_route_start_moves_elapsed_bucket_to_next_day() -> None:
    now = datetime(2026, 6, 6, 22, 15)

    start = effective_route_start(now, "afternoon")

    assert start == datetime(2026, 6, 7, 14, 0)


def test_effective_route_start_keeps_future_bucket_today() -> None:
    now = datetime(2026, 6, 6, 10, 15)

    start = effective_route_start(now, "afternoon")

    assert start == datetime(2026, 6, 6, 14, 0)
