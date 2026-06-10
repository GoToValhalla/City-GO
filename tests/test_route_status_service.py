from services.route_status_service import partial_reason, route_status


def test_route_status_marks_single_point_as_partial() -> None:
    assert route_status(1, 4) == "partial_route"


def test_route_status_marks_empty_route_as_no_route() -> None:
    assert route_status(0, 4) == "no_route"


def test_partial_reason_uses_near_start_warning() -> None:
    reason = partial_reason("no_route", ["Не нашли мест рядом с выбранным стартом."])
    assert reason == "few_candidates_near_start"
