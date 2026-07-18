from types import SimpleNamespace

from schemas.user_route import (
    UserRouteBuildRequest,
    UserRouteCorrectRequest,
    UserRoutePoint,
    UserRouteState,
)
from services.public_route_place_access import PublicRouteScope
from services.user_route_correct_service import UserRouteCorrectService
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
    assert "route_skeleton_preserved_after_edit" not in state.warnings
    assert "place_replaced" not in state.warnings
    assert "Маршрут собран с ограничениями по данным." in state.warnings
    assert all("_" not in warning for warning in state.warnings)


def test_rebuild_from_here_uses_existing_skeleton_new(monkeypatch) -> None:
    route = _route_state()
    request = UserRouteCorrectRequest(
        current_route=route,
        action="rebuild_from_here",
        current_lat=61.01,
        current_lng=69.02,
        new_time_budget_minutes=90,
    )
    loaded_places = [_place("1", "Anchor cafe", 61.0042, 69.0019, "cafe", 20)]
    calls = {}

    def fake_load_ordered_places(_db, current_route):
        calls["loaded_route_id"] = current_route.route_id
        return loaded_places

    class FakeRecalcService:
        def recalc(self, *, places, intent, revision, extra_warnings=None):
            calls["places"] = places
            calls["lat"] = intent.lat
            calls["lng"] = intent.lng
            calls["budget"] = intent.time_budget_minutes
            calls["revision"] = revision
            calls["extra_warnings"] = extra_warnings
            return route.model_copy(update={"revision": revision, "status": "corrected"})

    class ExplodingBuilderService:
        def build_route(self, **_kwargs):
            raise AssertionError("rebuild_from_here must not run the full route builder")

    monkeypatch.setattr("services.user_route_correct_service.resolve_route_scope", lambda *_args: PublicRouteScope(1, "khanty-mansiysk"))
    monkeypatch.setattr("services.user_route_correct_service.load_ordered_places", fake_load_ordered_places)
    monkeypatch.setattr("services.user_route_correct_service.UserRouteRecalcService", lambda: FakeRecalcService())
    monkeypatch.setattr("services.user_route_correct_service.RouteBuilderService", lambda: ExplodingBuilderService())

    result = UserRouteCorrectService().correct(SimpleNamespace(), request)

    assert result.accepted is True
    assert result.state is not None
    assert result.state.status == "corrected"
    assert calls["loaded_route_id"] == "route-1"
    assert calls["places"] == loaded_places
    assert calls["lat"] == 61.01
    assert calls["lng"] == 69.02
    assert calls["budget"] == 90
    assert calls["revision"] == 2


def _route_state() -> UserRouteState:
    intent = UserRouteBuildRequest(
        lat=61.0042,
        lng=69.0019,
        city_id="khanty-mansiysk",
        time_budget_minutes=240,
    )
    return UserRouteState(
        route_id="route-1",
        revision=1,
        status="ready",
        context=intent,
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(
                place_id="1",
                position=1,
                title="Anchor cafe",
                address="Test address",
                image_url="https://example.test/place.jpg",
                short_description="Test description",
                lat=61.0042,
                lng=69.0019,
                category="cafe",
                visit_minutes=20,
            )
        ],
    )


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
        lat=lat,
        lng=lng,
        category=category,
        visit_minutes=visit_minutes,
        score=0.8,
    )
