from types import SimpleNamespace

from schemas.user_route import UserRouteBuildRequest
from services.user_route_recalc_service import UserRouteRecalcService


def test_user_route_recalc_preserves_existing_skeleton_new() -> None:
    intent = UserRouteBuildRequest(
        lat=61.0042,
        lng=69.0019,
        city_id="khanty-mansiysk",
        time_budget_minutes=15,
    )
    places = [
        _place("1", "Anchor cafe", 61.0042, 69.0019, "cafe", 20),
        _place("2", "Far museum", 61.0500, 69.0800, "museum", 45),
    ]

    state = UserRouteRecalcService().recalc(
        places=places,
        intent=intent,
        revision=3,
        extra_warnings=["place_replaced"],
    )

    assert state.revision == 3
    assert state.total_places == 2
    assert [point.place_id for point in state.points] == ["1", "2"]
    assert state.status != "empty"
    assert "route_skeleton_preserved_after_edit" in state.warnings
    assert "place_replaced" in state.warnings


def _place(
    place_id: str,
    title: str,
    lat: float,
    lng: float,
    category: str,
    visit_minutes: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=place_id,
        title=title,
        address="Test address",
        image_url="https://example.test/place.jpg",
        short_description="Test description",
        source="test",
        lat=lat,
        lng=lng,
        category=category,
        average_visit_duration_minutes=visit_minutes,
        effective_visit_duration_minutes=None,
        opening_hours=None,
        effective_opening_hours={
            day: {"open": "00:00", "close": "23:59"}
            for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
        },
        outdoor=False,
    )
