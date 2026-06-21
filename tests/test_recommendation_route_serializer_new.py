from types import SimpleNamespace

from services.recommendation_route_serializer import serialize_final_route
from services.route_finalize_types import FinalRoute


def test_serialize_route_point_uses_safe_content_fallbacks_new() -> None:
    point = SimpleNamespace(
        place_id="1",
        city_slug="khanty-mansiysk",
        title="",
        address=None,
        image_url="",
        short_description=None,
        source=None,
        lat=61.0042,
        lng=69.0019,
        category="museum",
        visit_minutes=30,
        estimated_walk_minutes=20,
        scoring_breakdown={"route_assembly_fallback": "emergency_seed", "long_walk_segment": True},
    )
    final = FinalRoute(
        route_id="route-1",
        status="partial_route",
        points=[point],
        total_minutes=30,
        total_places=1,
        estimated_distance=1.5,
    )

    payload = serialize_final_route(final)

    serialized = payload["points"][0]
    assert serialized["title"] == "Место без названия"
    assert serialized["address"] == "Адрес уточняется"
    assert serialized["image_url"] is None
    assert serialized["scoring_breakdown"]["route_assembly_fallback"] == "emergency_seed"
    assert serialized["scoring_breakdown"]["long_walk_segment"] is True
