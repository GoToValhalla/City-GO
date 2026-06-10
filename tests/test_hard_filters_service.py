"""
Юнит-тесты services.hard_filters_service.HardFiltersService.

Места подменяются SimpleNamespace (без ORM), часы — через mock на is_place_open_at.
Важно: при len(отфильтрованного) < MIN_POOL_SIZE сервис вызывает _fallback и снова подмешивает
кандидатов из исходного списка; для проверок «строго пусто» временно ставим MIN_POOL_SIZE = 0.

Запуск:
  python3.11 -m pytest tests/test_hard_filters_service.py -q
"""

from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
import unittest.mock
from unittest.mock import patch

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.hard_filters_service import HardFiltersService


# Базовый MergedContext: поля как в реальном merge; overrides — точечные замены под сценарий.
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
        "effective_num_stops": 4,
        "min_stop_duration_minutes": 20,
    }
    data.update(overrides)
    return MergedContext(**data)


# Минимальный «Place» для _is_valid: id, category, price_level, opening_hours.
def _place(pid: int, **kwargs) -> SimpleNamespace:
    base = {
        "id": pid,
        "category": "cafe",
        "price_level": 2,
        "lat": 55.0,
        "lng": 20.0,
        "status": "active",
        "is_active": True,
        "opening_hours": {"mon": {"open": "09:00", "close": "18:00"}},
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


class TestHardFiltersService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = HardFiltersService()
        # Фиксированный момент времени для PASS1 «открыто сейчас» (день недели согласован с opening_hours в _place).
        self.now = datetime(2030, 6, 10, 12, 0, 0)

    def test_empty_input(self) -> None:
        self.assertEqual(self.svc.apply([], _ctx(), self.now), [])

    # Открыто сейчас → место остаётся (MIN_POOL_SIZE=0, чтобы не вызвать лишнюю логику fallback).
    @patch("services.hard_filters_service.is_place_open_at")
    def test_keeps_open_place(self, mock_open) -> None:
        mock_open.return_value = True
        places = [_place(1)]
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, _ctx(), self.now)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].id, 1)

    # Flexible режим не режет closed_now как hard filter.
    @patch("services.hard_filters_service.is_place_open_at")
    def test_keeps_closed_place_when_flexible(self, mock_open) -> None:
        mock_open.return_value = False
        places = [_place(1)]
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, _ctx(), self.now)
        self.assertEqual(len(out), 1)

    @patch("services.hard_filters_service.is_place_open_at")
    def test_drops_closed_place_when_now_mode(self, mock_open) -> None:
        mock_open.return_value = False
        places = [_place(1)]
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, _ctx(route_time_mode="now"), self.now)
        self.assertEqual(out, [])

    # Неизвестные часы (None от is_place_open_at) не отсекаем — fail-open на PASS1.
    @patch("services.hard_filters_service.is_place_open_at")
    def test_keeps_unknown_hours(self, mock_open) -> None:
        mock_open.return_value = None
        places = [_place(1)]
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, _ctx(), self.now)
        self.assertEqual(len(out), 1)

    @patch("services.hard_filters_service.is_place_open_at", return_value=None)
    def test_drops_unknown_hours_when_time_sensitive(self, _mock_open) -> None:
        places = [_place(1, opening_hours=None)]
        ctx = _ctx(route_time_mode="now")
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, ctx, self.now)
        self.assertEqual(out, [])

    @patch("services.hard_filters_service.is_place_open_at", return_value=True)
    def test_drops_closed_status_even_with_fallback(self, _mock_open) -> None:
        places = [_place(1, status="closed"), _place(2, status="temporarily_closed")]
        out = self.svc.apply(places, _ctx(), self.now)
        self.assertEqual(out, [])

    @patch("services.hard_filters_service.is_place_open_at", return_value=True)
    def test_drops_missing_coordinates(self, _mock_open) -> None:
        places = [_place(1, lat=None)]
        with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
            out = self.svc.apply(places, _ctx(), self.now)
        self.assertEqual(out, [])

    @patch("services.hard_filters_service.is_place_open_at", return_value=True)
    def test_report_contains_filter_reasons(self, _mock_open) -> None:
        places = [_place(1, status="closed"), _place(2)]
        report = self.svc.apply_with_report(places, _ctx(), self.now)
        self.assertEqual(report.reason_counts["status"], 1)

    # Категория из списка avoided_categories — жёстное исключение.
    def test_excludes_avoided_category(self) -> None:
        with patch("services.hard_filters_service.is_place_open_at", return_value=True):
            places = [_place(1, category="bar")]
            with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
                out = self.svc.apply(places, _ctx(avoided_categories=["bar"]), self.now)
            self.assertEqual(out, [])

    # price_level выше budget_level контекста — место отбрасывается.
    def test_excludes_high_price_vs_budget(self) -> None:
        with patch("services.hard_filters_service.is_place_open_at", return_value=True):
            places = [_place(1, price_level=4)]
            with unittest.mock.patch.object(HardFiltersService, "MIN_POOL_SIZE", 0):
                out = self.svc.apply(places, _ctx(budget_level=BudgetLevel.LOW), self.now)
            self.assertEqual(out, [])

    @patch("services.hard_filters_service.is_place_open_at", return_value=True)
    def test_fallback_refills_from_original_when_strict_pool_small(self, _mock) -> None:
        """При пуле < MIN_POOL_SIZE после строгого фильтра подмешивается ослабленный список (без категории/OH)."""
        ctx = _ctx(avoided_categories=["ghost"])
        places = [_place(1, category="cafe"), _place(2, category="museum")]
        out = self.svc.apply(places, ctx, self.now)
        self.assertGreaterEqual(len(out), 1)


if __name__ == "__main__":
    unittest.main()
