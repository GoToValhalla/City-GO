from services.explainability_service import ExplainabilityService
from services.route_finalize_service import FinalRoute


def test_explanation_includes_route_warnings_as_data_limitations() -> None:
    warning = "У части мест нет часов работы; время визита проверено приблизительно."
    route = FinalRoute(
        route_id="rid",
        points=[],
        total_minutes=0,
        total_places=0,
        estimated_distance=0.0,
        has_warnings=True,
        warning_count=1,
        warnings=[warning],
    )
    payload = ExplainabilityService().build_route_explanation(route)
    assert payload["warnings"] == [warning]
    assert payload["data_limitations"] == [warning]
