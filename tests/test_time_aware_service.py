"""
Юнит-тесты TimeAwareService: time_status, time_warning, arrival/departure, walk.

Запуск:
  python3.11 -m unittest tests.test_time_aware_service -v
"""

from __future__ import annotations

import unittest
from datetime import datetime

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_service import RoutePoint
from services.time_aware_service import TimeAwareService


def _ctx(timezone: str = "UTC") -> MergedContext:
    return MergedContext(
        location=(55.0, 20.0),
        city_id=None,
        timezone=timezone,
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


def _monday_open_9_21() -> dict:
    return {"mon": {"open": "09:00", "close": "21:00"}}


class TestTimeAwareServiceScenarioAOk(unittest.TestCase):
    """A: место открыто к arrival и на всё время визита → ok."""

    def test_all_ok_when_open_for_full_visit(self) -> None:
        svc = TimeAwareService()
        # Понедельник 2030-06-03 10:00 UTC — внутри окна 09–21
        start = datetime(2030, 6, 3, 10, 0, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.001,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=25,
            opening_hours=_monday_open_9_21(),
        )
        out = svc.apply([p], _ctx(), start)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].time_status, "ok")
        self.assertIsNone(out[0].time_warning)
        self.assertGreaterEqual(out[0].estimated_walk_minutes, 1)
        self.assertIsNotNone(out[0].estimated_arrival_time)
        self.assertIsNotNone(out[0].estimated_departure_time)
        self.assertGreater(
            out[0].estimated_departure_time,
            out[0].estimated_arrival_time,
        )


class TestTimeAwareServiceTimezone(unittest.TestCase):
    def test_naive_utc_start_is_checked_in_city_timezone(self) -> None:
        svc = TimeAwareService()
        # 04:00 UTC is 09:00 in Asia/Yekaterinburg / Khanty-Mansiysk style timezone.
        start = datetime(2030, 6, 3, 4, 0, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.0,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=25,
            opening_hours=_monday_open_9_21(),
        )

        out = svc.apply([p], _ctx("Asia/Yekaterinburg"), start)

        self.assertEqual(out[0].time_status, "ok")
        self.assertEqual(out[0].estimated_arrival_time.tzinfo.key, "Asia/Yekaterinburg")
        self.assertEqual(out[0].estimated_arrival_time.hour, 9)


class TestTimeAwareServiceScenarioBClosed(unittest.TestCase):
    """B: закрыто к моменту arrival → closed_at_arrival."""

    def test_closed_at_arrival(self) -> None:
        svc = TimeAwareService()
        start = datetime(2030, 6, 3, 8, 0, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.002,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=20,
            opening_hours=_monday_open_9_21(),
        )
        out = svc.apply([p], _ctx(), start)
        self.assertEqual(out[0].time_status, "closed_at_arrival")
        self.assertIsNotNone(out[0].time_warning)


class TestTimeAwareServiceWaitGap(unittest.TestCase):
    def test_small_wait_gap_shifts_arrival_to_opening_time(self) -> None:
        svc = TimeAwareService()
        start = datetime(2030, 6, 3, 8, 40, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.001,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=20,
            opening_hours=_monday_open_9_21(),
        )
        out = svc.apply([p], _ctx(), start)
        self.assertEqual(out[0].time_status, "wait_before_opening")
        self.assertEqual(out[0].estimated_arrival_time.hour, 9)
        self.assertEqual(out[0].estimated_arrival_time.minute, 0)
        self.assertIsNotNone(out[0].time_warning)


class TestTimeAwareServiceScenarioCUnknown(unittest.TestCase):
    """C: opening_hours отсутствуют → hours_unknown."""

    def test_hours_unknown_when_no_opening_hours(self) -> None:
        svc = TimeAwareService()
        start = datetime(2030, 6, 3, 12, 0, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.001,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=30,
            opening_hours=None,
        )
        out = svc.apply([p], _ctx(), start)
        self.assertEqual(out[0].time_status, "hours_unknown")
        self.assertIsNotNone(out[0].time_warning)


class TestTimeAwareServiceScenarioClosesDuring(unittest.TestCase):
    def test_closes_during_visit(self) -> None:
        svc = TimeAwareService()
        start = datetime(2030, 6, 3, 20, 0, 0)
        p = RoutePoint(
            place_id="1",
            lat=55.001,
            lng=20.0,
            score=0.9,
            category="cafe",
            visit_minutes=120,
            opening_hours=_monday_open_9_21(),
        )
        out = svc.apply([p], _ctx(), start)
        self.assertEqual(out[0].time_status, "closes_during_visit")
        self.assertIsNotNone(out[0].time_warning)


class TestTimeAwareServiceOrderPreserved(unittest.TestCase):
    def test_does_not_drop_points(self) -> None:
        svc = TimeAwareService()
        start = datetime(2030, 6, 3, 10, 0, 0)
        a = RoutePoint("1", 55.001, 20.0, 0.5, "cafe", 10, None)
        b = RoutePoint("2", 55.002, 20.001, 0.5, "park", 10, None)
        out = svc.apply([a, b], _ctx(), start)
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0].place_id, "1")
        self.assertEqual(out[1].place_id, "2")


if __name__ == "__main__":
    unittest.main()