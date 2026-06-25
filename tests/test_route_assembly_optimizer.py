from types import SimpleNamespace

import allure
import pytest

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_optimizer import assemble_route
from services.scoring_service import ScoredPlace
from tests.allure_support import attach_json, given, scenario, then, when

pytestmark = [pytest.mark.routing, pytest.mark.integration, pytest.mark.regression]


class RoutePointStub:
    def __init__(self, place_id, lat, lng, score, category, visit_minutes, **kwargs):
        self.place_id = place_id
        self.lat = lat
        self.lng = lng
        self.score = score
        self.category = category
        self.visit_minutes = visit_minutes
        for key, value in kwargs.items():
            setattr(self, key, value)


def _ctx(time_budget_minutes=120):
    return MergedContext(
        location=(54.96, 20.48), city_id="zelenogradsk", time_budget_minutes=time_budget_minutes,
        effective_time_budget_minutes=int(time_budget_minutes * 0.8), time_of_day=None,
        route_time_mode="flexible", interests=["walk", "sea"], avoided_categories=[],
        avoided_place_ids=[], budget_level=BudgetLevel.MID, pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0, local_vs_tourist=0.5, novelty_mode=False, is_visiting=False,
        visit_city_id=None, visit_days=1, radius_meters=1500, effective_num_stops=3,
        min_stop_duration_minutes=20,
    )


def _place(place_id, title, lat, lng, category, visit_minutes, score):
    place = SimpleNamespace(
        id=place_id, title=title, lat=lat, lng=lng, category=category,
        average_visit_duration_minutes=visit_minutes, effective_visit_duration_minutes=visit_minutes,
        opening_hours=None, effective_opening_hours={"mon": {"open": "00:00", "close": "23:59"}},
        price_level=1, public_image_url=None, short_description=None, source="test",
        city=SimpleNamespace(slug="zelenogradsk"), validation={"is_valid": True, "issues": []},
    )
    return ScoredPlace(place, score, {"test": score})


@scenario("Сборщик ослабляет бюджет, чтобы маршрут не состоял из одной точки", epic="Маршруты", feature="Сборка маршрута", story="Fallback временного бюджета", severity=allure.severity_level.CRITICAL)
def test_assembly_relaxes_budget_when_one_point_would_stop_route():
    with given("есть три близкие валидные точки с разной длительностью посещения"):
        scored = [
            _place(1, "Променад", 54.9601, 20.4801, "walk", 45, 0.95),
            _place(2, "Кофе", 54.9602, 20.4802, "cafe", 30, 0.85),
            _place(3, "Сквер", 54.9603, 20.4803, "walk", 45, 0.80),
        ]
        attach_json("Кандидаты", [{"id": item.place.id, "title": item.place.title, "score": item.score} for item in scored])
    with when("сборщик строит маршрут на 120 минут"):
        route = assemble_route(scored, _ctx(120), RoutePointStub)
        attach_json("Собранный порядок", [point.place_id for point in route])
    with then("маршрут содержит минимум две точки и начинается с лучшего кандидата"):
        assert len(route) >= 2
        assert route[0].place_id == "1"


@scenario("Сборщик возвращает пустой маршрут при отсутствии кандидатов", epic="Маршруты", feature="Сборка маршрута", story="Явное пустое состояние", severity=allure.severity_level.NORMAL)
def test_assembly_keeps_empty_route_when_candidates_absent():
    with given("список кандидатов пуст"):
        candidates = []
    with when("сборщик пытается построить маршрут"):
        route = assemble_route(candidates, _ctx(120), RoutePointStub)
    with then("результат остаётся пустым без искусственных точек"):
        assert route == []
