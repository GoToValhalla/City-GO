from __future__ import annotations

from datetime import datetime, timezone

from services.route_start_time import effective_route_start


def test_effective_route_start_assumes_naive_input_is_utc_new() -> None:
    start = effective_route_start(datetime(2030, 6, 3, 7, 0, 0), None)

    assert start.tzinfo == timezone.utc
    assert start.isoformat() == "2030-06-03T07:00:00+00:00"


def test_effective_route_start_keeps_timezone_for_named_bucket_new() -> None:
    start = effective_route_start(datetime(2030, 6, 3, 7, 0, 0, tzinfo=timezone.utc), "morning")

    assert start.tzinfo == timezone.utc
    assert start.isoformat() == "2030-06-03T09:00:00+00:00"
