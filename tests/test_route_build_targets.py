from schemas.merged_context import compute_num_stops
from services.route_status_service import route_status


def test_compute_num_stops_uses_target_route_shape() -> None:
    assert compute_num_stops(15, 1.0) == 3
    assert compute_num_stops(60, 1.0) == 3
    assert compute_num_stops(120, 1.0) == 4
    assert compute_num_stops(180, 1.0) == 6
    assert compute_num_stops(300, 1.0) == 8


def test_route_status_uses_soft_ready_thresholds() -> None:
    assert route_status(0, 3) == "no_route"
    assert route_status(1, 3) == "partial_route"
    assert route_status(2, 3) == "ready"
    assert route_status(3, 3) == "ready"
    assert route_status(2, 4) == "partial_route"
    assert route_status(3, 4) == "ready"
    assert route_status(4, 4) == "ready"
    assert route_status(4, 6) == "partial_route"
    assert route_status(5, 6) == "ready"
