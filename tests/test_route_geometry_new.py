from services.route_geometry import walk_minutes_between
from services.time_aware_math import walk_minutes


def test_time_aware_walk_minutes_uses_shared_route_geometry_new() -> None:
    lat1, lng1 = 61.0042, 69.0019
    lat2, lng2 = 61.0500, 69.0800

    assert walk_minutes(lat1, lng1, lat2, lng2) == walk_minutes_between(lat1, lng1, lat2, lng2)
