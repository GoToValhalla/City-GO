"""
Юнит-тесты services.route_assembly_service.RouteAssemblyService.

Вход — список ScoredPlace с duck-typed place (SimpleNamespace), как в smoke pipeline.
Проверяем только сборку порядка и ограничение по времени, без БД и без time-aware шага.

Запуск:
  python3.11 -m pytest tests/test_route_assembly_service.py -q
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_service import RouteAssemblyService
from services.route_quality_score import build_route_quality_score, minimum_points_for_budget, public_quality_warnings
from services.scoring_service import ScoredPlace


# Тот же шаблон контекста, что и в других тестах pipeline; overrides — только отличия сценария.
def _ctx(**overrides) -> MergedContext:
    data = {
        "location": (55.0, 20.0),
        "city_id": None,
        "time_budget_minutes": 120,
        "effective_time_budget_minutes": 96,
        "interests": [],
        "avoided_categories": [],
        "avoided_place_ids": [],
        "budget_level": BudgetLevel.MID,
        "pace_mode": PaceMode.NORMAL,
        "pace_multiplier": 1.0,
        "local_vs_tourist": 0.5,
        "novelty_mode": False,
        "is_visiting": False,
        "visit_city_id": None,
        "visit_days": 1,
        "radius_meters": 1500,
        "effective_num_stops": 6,
        "min_stop_duration_minutes": 5,
    }
    data.update(overrides)
    return MergedContext(**data)


# Упрощённая сущность места: поля, которые читает assembly/scoring при сборке RoutePoint.
def _place(pid: int, lat: float, lng: float, category: str = "cafe") -> SimpleNamespace:
    return SimpleNamespace(
        id=pid,
        slug=f"p{pid}",
        title=f"P{pid}",
        lat=lat,
        lng=lng,
        category=category,
        outdoor=False,
        indoor=True,
        dog_friendly=False,
        family_friendly=False,
        price_level=2,
        opening_hours=None,
        average_visit_duration_minutes=20,
    )


# Обёртка места с числовым score; breakdown здесь не влияет на порядок сборки.
def _scored(place: SimpleNamespace, score: float) -> ScoredPlace:
    return ScoredPlace(place=place, score=score, breakdown={})


class TestRouteAssemblyService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = RouteAssemblyService()

    # Нет кандидатов — пустой маршрут без ошибок.
    def test_empty_candidates(self) -> None:
        route = self.svc.build([], _ctx())
        self.assertEqual(route, [])

    # Один кандидат с достаточным бюджетом времени → ровно одна точка, place_id строкой.
    def test_single_point_route(self) -> None:
        p = _place(1, 55.0, 20.0)
        scored = [_scored(p, 0.9)]
        route = self.svc.build(scored, _ctx(effective_time_budget_minutes=200))
        self.assertEqual(len(route), 1)
        self.assertEqual(route[0].place_id, "1")
        self.assertGreater(route[0].visit_minutes, 0)

    # Маленький effective_time_budget: первая точка забирает визит-минуты, цикл не добавляет вторую.
    def test_respects_time_budget_stops_growth(self) -> None:
        """Очень маленький бюджет времени — не более одной точки (визит съедает остаток)."""
        places = [
            _scored(_place(1, 55.0, 20.0), 1.0),
            _scored(_place(2, 55.001, 20.001), 0.95),
        ]
        route = self.svc.build(
            places,
            _ctx(
                effective_time_budget_minutes=15,
                effective_num_stops=6,
                min_stop_duration_minutes=5,
            ),
        )
        self.assertLessEqual(len(route), 1)

    def test_counts_walk_time_before_selecting_candidate(self) -> None:
        far = _place(1, 55.2, 20.2)
        near = _place(2, 55.0001, 20.0001)
        route = self.svc.build(
            [_scored(far, 1.0), _scored(near, 0.7)],
            _ctx(effective_time_budget_minutes=35, effective_num_stops=2),
        )
        self.assertEqual([point.place_id for point in route], ["2"])

    def test_limits_repeated_category(self) -> None:
        scored = [
            _scored(_place(pid, 55.0 + pid * 0.0001, 20.0, "coffee"), 1.0 - pid * 0.01)
            for pid in range(1, 6)
        ]
        route = self.svc.build(scored, _ctx(effective_time_budget_minutes=300))
        self.assertEqual(len(route), 5)
        self.assertTrue(all(point.category == "coffee" for point in route))

    def test_local_loop_cleanup_swaps_obvious_backtrack(self) -> None:
        first = _place(1, 55.0001, 20.0001, "museum")
        far = _place(2, 55.0, 20.01, "park")
        close_to_first = _place(3, 55.0002, 20.0002, "walk")
        route = self.svc.build(
            [_scored(first, 0.9), _scored(far, 0.95), _scored(close_to_first, 0.8)],
            _ctx(effective_time_budget_minutes=300, effective_num_stops=3),
        )
        self.assertEqual([point.place_id for point in route], ["2", "3", "1"])

    def test_quality_minimum_points_for_budget(self) -> None:
        self.assertEqual(minimum_points_for_budget(15), 1)
        self.assertEqual(minimum_points_for_budget(44), 1)
        self.assertEqual(minimum_points_for_budget(45), 3)
        self.assertEqual(minimum_points_for_budget(89), 3)
        self.assertEqual(minimum_points_for_budget(90), 4)

    def test_quality_empty_route_is_failed(self) -> None:
        quality = build_route_quality_score([], expected_stops=4, budget_minutes=120, warnings=[])
        self.assertEqual(quality.score, 0.0)
        self.assertEqual(quality.status, "failed")
        self.assertEqual(quality.actual_points, 0)
        self.assertEqual(quality.minimum_points, 4)

    def test_quality_short_budget_route_is_not_failed(self) -> None:
        route = self.svc.build([_scored(_place(1, 55.0, 20.0, "museum"), 1.0)], _ctx(effective_time_budget_minutes=30, effective_num_stops=1))
        quality = build_route_quality_score(route, expected_stops=1, budget_minutes=30, warnings=[])
        self.assertNotEqual(quality.status, "failed")

    def test_quality_short_large_budget_route_is_failed(self) -> None:
        route = self.svc.build([_scored(_place(1, 55.0, 20.0, "museum"), 1.0)], _ctx(effective_time_budget_minutes=120, effective_num_stops=4))
        quality = build_route_quality_score(route, expected_stops=4, budget_minutes=120, warnings=[])
        self.assertEqual(quality.status, "failed")

    def test_public_quality_warnings_are_unique_and_data_aware(self) -> None:
        route = self.svc.build(
            [_scored(_place(1, 55.0, 20.0, "museum"), 1.0), _scored(_place(2, 55.001, 20.001, "park"), 0.9)],
            _ctx(effective_time_budget_minutes=90, effective_num_stops=4),
        )
        route[0].address = None
        route[0].image_url = None
        route[0].short_description = None
        route[0].estimated_walk_minutes = 20
        warnings = public_quality_warnings(route, budget_minutes=90, warnings=["some_places_have_no_address"])
        self.assertEqual(warnings.count("some_places_have_no_address"), 1)
        self.assertIn("some_places_have_no_photo", warnings)
        self.assertIn("some_places_have_weak_description", warnings)
        self.assertIn("route_has_long_walk_segments", warnings)


if __name__ == "__main__":
    unittest.main()
