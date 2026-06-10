from types import SimpleNamespace

from services.explainability_service import ExplainabilityService
from services.route_finalize_service import FinalRoute


def test_explanation_payload_has_required_fields_and_time_status() -> None:
    point = SimpleNamespace(
        place_id="p1",
        category="park",
        time_status="ok",
        time_warning=None,
        hours_status="open",
        estimated_walk_minutes=3,
        scoring_breakdown={"interest": 0.9, "time_context": 0.5},
    )
    route = FinalRoute(
        route_id="rid-1",
        points=[point],
        total_minutes=60,
        total_places=1,
        estimated_distance=1.5,
        total_estimated_minutes=60,
    )
    payload = ExplainabilityService().build_route_explanation(route)
    assert payload["route_id"] == "rid-1"
    assert payload["summary"]
    assert payload["has_warnings"] is False
    assert payload["warning_count"] == 0
    assert len(payload["points"]) == 1
    assert payload["points"][0]["place_id"] == "p1"
    assert payload["points"][0]["time_status"] == "ok"
    assert payload["points"][0]["match_type"] == "proximity"
    assert payload["points"][0]["score_components"]["interest"] == 0.9
