"""
Юнит-тесты RouteFinalizeService и метрик FinalRoute после Time-Aware.

Запуск:
  python3.11 -m unittest tests.test_route_finalize_service -v
"""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_finalize_service import FinalRoute, RouteFinalizeService

# Текст route-level предупреждения при проблемах visit_duration (должен совпадать с route_finalize_service).
_VISIT_DURATION_ROUTE_WARNING = "Для некоторых мест использовано приблизительное время визита."


def _ctx() -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id=None,
        time_budget_minutes=120,
        effective_time_budget_minutes=96,
        interests=[],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=1500,
        effective_num_stops=4,
        min_stop_duration_minutes=20,
    )


def _point(
    place_id: str,
    lat: float,
    lng: float,
    visit_minutes: int,
    *,
    time_status: str = "ok",
    time_warning: str | None = None,
    estimated_arrival_time: datetime | None = None,
    estimated_departure_time: datetime | None = None,
    estimated_walk_minutes: int = 0,
    validation: dict | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        place_id=place_id,
        lat=lat,
        lng=lng,
        visit_minutes=visit_minutes,
        score=0.5,
        category="cafe",
        time_status=time_status,
        time_warning=time_warning,
        estimated_arrival_time=estimated_arrival_time,
        estimated_departure_time=estimated_departure_time,
        estimated_walk_minutes=estimated_walk_minutes,
        validation=validation,
    )


class TestRouteFinalizeNoWarnings(unittest.TestCase):
    def test_finalize_no_warnings(self) -> None:
        svc = RouteFinalizeService()
        t0 = datetime(2030, 1, 1, 10, 0, 0)
        route = [
            _point("1", 55.0, 20.0, 20, time_status="ok", estimated_arrival_time=t0, estimated_departure_time=t0 + timedelta(minutes=20)),
            _point("2", 55.01, 20.0, 25, time_status="ok", estimated_arrival_time=t0 + timedelta(minutes=30), estimated_departure_time=t0 + timedelta(minutes=55)),
        ]
        fr = svc.finalize(route, _ctx())
        self.assertTrue(fr.has_warnings)
        self.assertEqual(fr.warning_count, 3)
        self.assertEqual(fr.places_with_warnings, [])
        self.assertEqual(fr.warnings, ["some_places_have_no_address", "some_places_have_no_photo", "some_places_have_weak_description"])
        self.assertGreaterEqual(fr.total_walk_distance_meters, 0)
        self.assertEqual(fr.category_distribution["cafe"], 2)
        self.assertEqual(fr.time_breakdown["visit_time_minutes"], 45.0)

    def test_finalize_builds_user_warnings(self) -> None:
        svc = RouteFinalizeService()
        route = [_point("1", 55.0, 20.0, 20, time_status="ok")]
        fr = svc.finalize(route, _ctx(), extra_warnings=["Маршрут сокращён, чтобы уложиться в выбранный бюджет времени."])
        from services.route_user_warnings import user_warnings
        warnings = user_warnings(fr)
        self.assertEqual(warnings[0]["type"], "budget")
        self.assertEqual(warnings[0]["severity"], "info")


class TestRouteFinalizeWithWarnings(unittest.TestCase):
    def test_finalize_with_warnings(self) -> None:
        svc = RouteFinalizeService()
        t0 = datetime(2030, 1, 1, 10, 0, 0)
        route = [
            _point(
                "1",
                55.0,
                20.0,
                20,
                time_status="closed_at_arrival",
                time_warning="closed",
                estimated_arrival_time=t0,
                estimated_departure_time=t0 + timedelta(minutes=20),
            ),
            _point("2", 55.01, 20.0, 25, time_status="ok", estimated_arrival_time=t0 + timedelta(minutes=25), estimated_departure_time=t0 + timedelta(minutes=50)),
        ]
        fr = svc.finalize(route, _ctx())
        self.assertTrue(fr.has_warnings)
        self.assertGreaterEqual(fr.warning_count, 1)
        self.assertIn("1", fr.places_with_warnings)


class TestRouteFinalizeTimeCalculation(unittest.TestCase):
    def test_finalize_time_calculation(self) -> None:
        svc = RouteFinalizeService()
        t_start = datetime(2030, 6, 3, 10, 0, 0)
        t_first_dep = t_start + timedelta(minutes=30)
        t_second_arr = t_start + timedelta(minutes=40)
        t_end = t_start + timedelta(minutes=90)
        route = [
            _point("a", 55.0, 20.0, 30, estimated_arrival_time=t_start, estimated_departure_time=t_first_dep),
            _point("b", 55.02, 20.0, 50, estimated_arrival_time=t_second_arr, estimated_departure_time=t_end),
        ]
        fr = svc.finalize(route, _ctx())
        self.assertEqual(fr.total_estimated_minutes, 90)
        self.assertEqual(fr.estimated_end_time, t_end)


class TestRouteFinalizeEmptyRoute(unittest.TestCase):
    def test_finalize_empty_route(self) -> None:
        svc = RouteFinalizeService()
        fr: FinalRoute = svc.finalize([], _ctx())
        self.assertEqual(fr.status, "empty")
        self.assertEqual(fr.total_places, 0)
        self.assertEqual(fr.quality_status, "failed")
