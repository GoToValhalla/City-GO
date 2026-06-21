from types import SimpleNamespace

from services.route_finalize_types import FinalRoute


def test_final_route_exposes_places_alias_for_trace_compatibility() -> None:
    points = [SimpleNamespace(place_id="1")]

    final = FinalRoute(
        route_id="route-1",
        points=points,
        total_minutes=30,
        total_places=1,
        estimated_distance=0.5,
    )

    assert final.points == points
    assert final.places == points
