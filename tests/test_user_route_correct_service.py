from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from schemas.user_route import UserRouteCorrectRequest, UserRouteIntent, UserRoutePoint, UserRouteState
from services.route_finalize_service import FinalRoute
from services.user_route_correction_policy import shorten_target_place_id
from services.user_route_correct_service import UserRouteCorrectService
from services.user_route_replacement_loader import find_replacement_place


class _Query:
    def __init__(self, places):
        self._places = places

    def filter(self, *_args):
        return self

    def all(self):
        return self._places

    def first(self):
        return self._places[0] if self._places else None


class _Db:
    def __init__(self, places):
        self._places = places

    def query(self, *_args):
        return _Query(self._places)


def _place(place_id: int, category: str = "cafe"):
    return SimpleNamespace(
        id=place_id,
        lat=54.96 + place_id / 1000,
        lng=20.48,
        category=category,
        opening_hours=None,
        average_visit_duration_minutes=20,
    )


def _state() -> UserRouteState:
    return UserRouteState(
        route_id="route",
        context=UserRouteIntent(lat=54.96, lng=20.48, time_budget_minutes=120),
        total_places=2,
        total_minutes=40,
        total_estimated_minutes=45,
        estimated_distance=1.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(place_id="1", position=1, lat=54.961, lng=20.48, category="cafe", visit_minutes=20),
            UserRoutePoint(place_id="2", position=2, lat=54.962, lng=20.48, category="museum", visit_minutes=20),
        ],
    )


def _point(place_id: str, position: int, score: float, minutes: int) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=place_id,
        position=position,
        lat=54.96 + int(place_id) / 1000,
        lng=20.48,
        category="cafe",
        visit_minutes=minutes,
        scoring_breakdown={"interest": score},
    )


def test_remove_place_recalculates_current_route() -> None:
    request = UserRouteCorrectRequest(current_route=_state(), action="remove_place", target_place_id="1")
    result = UserRouteCorrectService().correct(_Db([_place(1), _place(2, "museum")]), request)
    assert result.revision == 2
    assert [point.place_id for point in result.points] == ["2"]


def test_shorten_route_selects_lowest_value_per_minute() -> None:
    state = _state().model_copy(
        update={"points": [_point("1", 1, 0.9, 20), _point("2", 2, 0.1, 20), _point("3", 3, 0.8, 60)]}
    )
    assert shorten_target_place_id(state) == "2"


def test_replacement_loader_finds_same_category_not_in_route() -> None:
    with patch("services.user_route_replacement_loader.resolve_route_city_id", return_value=1):
        replacement = find_replacement_place(
            _Db([_place(1), _place(2, "museum"), _place(3)]),
            route=_state(),
            category="cafe",
            excluded_ids={"1", "2"},
        )
    assert replacement is not None
    assert replacement.id == 3


def test_avoid_category_rebuilds_with_target_category() -> None:
    request = UserRouteCorrectRequest(current_route=_state(), action="avoid_category", target_place_id="2")
    final = FinalRoute("new", [], 0, 0, 0.0)
    builder = MagicMock()
    builder.build_route.return_value = final
    with patch("services.user_route_correct_service.RouteBuilderService", return_value=builder):
        result = UserRouteCorrectService().correct(_Db([_place(2, "museum")]), request)
    called_request = builder.build_route.call_args.kwargs["request"]
    assert result.route_id == "new"
    assert called_request.avoided_categories == ["museum"]
