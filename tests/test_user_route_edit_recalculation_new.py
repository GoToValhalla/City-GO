"""Expected route edit behavior: edits must recalculate route summaries."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from schemas.user_route import UserRouteAddPlaceRequest, UserRouteIntent, UserRoutePoint, UserRouteState
from services.user_route_edit_service import UserRouteEditService

F = TypeVar("F", bound=Callable[..., Any])

try:  # pragma: no cover - allure is optional in the current dependency set.
    import allure  # type: ignore
except ImportError:  # pragma: no cover
    class _AllureNoop:
        def epic(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def feature(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def story(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def severity(self, _level: str) -> Callable[[F], F]:
            return lambda func: func

    allure = _AllureNoop()


def _point(place, position: int) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=str(place.id),
        city_slug="route-edit-city",
        position=position,
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        lat=float(place.lat),
        lng=float(place.lng),
        category=str(place.category or "museum"),
        visit_minutes=20,
    )


@allure.epic("City Go Routes")
@allure.feature("Live Route Editing")
@allure.story("Add place recalculates route totals and map inputs")
@allure.severity("critical")
def test_add_place_recalculates_route_summary_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-edit-city")
    first = place_factory(city_id=city.id, slug="first", title="Первая точка", category="museum", lat=54.9600, lng=20.4700)
    second = place_factory(city_id=city.id, slug="second", title="Вторая точка", category="park", lat=54.9650, lng=20.4750)
    third = place_factory(city_id=city.id, slug="third", title="Третья точка", category="culture", lat=54.9700, lng=20.4800)

    current_route = UserRouteState(
        route_id="test-route",
        revision=1,
        status="ready",
        context=UserRouteIntent(lat=54.9600, lng=20.4700, city_id=city.slug, time_budget_minutes=180),
        total_places=2,
        total_minutes=40,
        total_estimated_minutes=40,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[_point(first, 1), _point(second, 2)],
    )

    result = UserRouteEditService().add_place(
        db_session,
        UserRouteAddPlaceRequest(
            current_route=current_route,
            place_id=str(third.id),
            insert_after_place_id=str(second.id),
        ),
    )

    assert result.accepted is True
    assert result.state is not None
    next_route = result.state
    assert next_route.revision == 2
    assert next_route.total_places == 3
    assert [point.place_id for point in next_route.points] == [str(first.id), str(second.id), str(third.id)]
    assert next_route.total_estimated_minutes > current_route.total_estimated_minutes
    assert next_route.total_walk_distance_meters >= 0
    assert next_route.time_breakdown
    assert next_route.category_distribution["museum"] == 1
    assert next_route.category_distribution["park"] == 1
    assert next_route.category_distribution["culture"] == 1
