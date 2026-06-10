"""
Юнит-тесты ExplainabilityService (STEP 8 payload поверх FinalRoute).

Запуск:
  python3.11 -m unittest tests.test_explainability_service -v
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from services.explainability_service import ExplainabilityService
from services.route_finalize_service import FinalRoute


def _final_route(
    *,
    points: list,
    total_minutes: int = 60,
    total_estimated_minutes: int = 0,
    has_warnings: bool = False,
    warning_count: int = 0,
) -> FinalRoute:
    te = total_estimated_minutes if total_estimated_minutes > 0 else total_minutes
    return FinalRoute(
        route_id="rid-1",
        points=points,
        total_minutes=total_minutes,
        total_places=len(points),
        estimated_distance=1.5,
        total_estimated_minutes=te,
        estimated_end_time=None,
        has_warnings=has_warnings,
        warning_count=warning_count,
        places_with_warnings=[],
    )


class TestExplainabilityNoWarnings(unittest.TestCase):
    def test_summary_without_warning_phrase(self) -> None:
        svc = ExplainabilityService()
        p = SimpleNamespace(place_id="1", category="cafe")
        route = _final_route(points=[p], warning_count=0, has_warnings=False)
        s = svc.build_route_summary(route)
        self.assertNotIn("предупреждения", s.casefold())
        self.assertIn("примерно", s)

    def test_point_reason_uses_scoring_breakdown(self) -> None:
        svc = ExplainabilityService()
        p = SimpleNamespace(
            place_id="1",
            category="museum",
            estimated_walk_minutes=0,
            scoring_breakdown={"interest": 0.95, "time_context": 0.2},
        )
        payload = svc._point_payload(p)
        self.assertEqual(payload["match_type"], "interest")
        self.assertIn("интерес", str(payload["reason"]).casefold())


class TestExplainabilityWithWarnings(unittest.TestCase):
    def test_summary_contains_warning_phrase_and_count(self) -> None:
        svc = ExplainabilityService()
        p = SimpleNamespace(place_id="1", category="cafe")
        route = _final_route(points=[p], has_warnings=True, warning_count=2)
        s = svc.build_route_summary(route)
        self.assertIn("предупреждения", s.casefold())
        self.assertIn("2", s)


class TestExplainabilityTimeWarningPriority(unittest.TestCase):
    def test_time_warning_used_when_set(self) -> None:
        svc = ExplainabilityService()
        p = SimpleNamespace(
            place_id="1",
            category="cafe",
            time_warning="Явное предупреждение Time-Aware",
            hours_status="closed",
        )
        w = svc.build_point_warning(p)
        self.assertEqual(w, "Явное предупреждение Time-Aware")


class TestExplainabilityHoursStatusFallback(unittest.TestCase):
    def test_hours_status_when_no_time_warning(self) -> None:
        svc = ExplainabilityService()
        p = SimpleNamespace(
            place_id="1",
            category="museum",
            time_warning=None,
            hours_status="closed",
        )
        w = svc.build_point_warning(p)
        self.assertIn("закрыто", w.casefold())


if __name__ == "__main__":
    unittest.main()
