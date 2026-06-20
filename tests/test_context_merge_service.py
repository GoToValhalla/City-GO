"""
Юнит-тесты services.context_merge_service.ContextMergeService и RequestContext.

Проверяем только слой merge (без БД и без последующих шагов pipeline).
Имена тестов = сценарий; внутри — проверки инвариантов MergedContext.

Запуск:
  python3.11 -m pytest tests/test_context_merge_service.py -q
"""

from __future__ import annotations

import unittest

from schemas.merged_context import BudgetLevel, PaceMode
from schemas.user_profile import UserBehaviorProfile, UserHistory, UserProfile, UserStaticPreferences
from services.context_merge_service import ContextMergeService, RequestContext


class TestContextMergeService(unittest.TestCase):
    def setUp(self) -> None:
        self.svc = ContextMergeService()

    # Базовый запрос: только координаты + интересы — остальное из дефолтов сервиса.
    def test_merge_minimal_request_defaults(self) -> None:
        req = RequestContext(
            location=(55.0, 20.0),
            time_budget_minutes=None,
            interests=["cafe"],
        )
        ctx = self.svc.merge(req, profile=None)

        self.assertEqual(ctx.location, (55.0, 20.0))
        self.assertEqual(ctx.time_budget_minutes, self.svc.DEFAULT_TIME_BUDGET)
        self.assertEqual(ctx.interests, ["cafe"])
        self.assertEqual(ctx.budget_level, BudgetLevel.MID)
        self.assertEqual(ctx.pace_mode, PaceMode.NORMAL)
        self.assertFalse(ctx.novelty_mode)
        self.assertGreater(ctx.radius_meters, 0)
        self.assertEqual(ctx.route_time_mode, "flexible")
        self.assertGreaterEqual(ctx.effective_num_stops, 1)

    def test_merge_empty_interests_stays_empty(self) -> None:
        ctx = self.svc.merge(RequestContext(location=(55.0, 20.0), interests=[]), profile=None)
        self.assertEqual(ctx.interests, [])

    def test_interest_conflict_with_avoided_category_is_normalized(self) -> None:
        ctx = self.svc.merge(
            RequestContext(
                location=(55.0, 20.0),
                interests=["coffee", "museum", "walk"],
                avoided_categories=["museums"],
            ),
            profile=None,
        )

        self.assertEqual(ctx.avoided_categories, ["museum"])
        self.assertNotIn("museum", ctx.interests)
        self.assertCountEqual(ctx.interests, ["coffee", "walk"])
        self.assertEqual(ctx.interest_removed_due_to_avoidance, ["museum"])

    # Если в запросе нет time_budget, подставляется preferred_time_budget_minutes из профиля.
    def test_merge_time_budget_from_profile(self) -> None:
        req = RequestContext(location=(1.0, 2.0), time_budget_minutes=None)
        profile = UserProfile(
            behavior=UserBehaviorProfile(preferred_time_budget_minutes=90),
        )
        ctx = self.svc.merge(req, profile=profile)
        self.assertEqual(ctx.time_budget_minutes, 90)

    # Интересы из запроса и из профиля объединяются (множество без дубликатов по смыслу assertCountEqual).
    def test_merge_interests_union_request_and_profile(self) -> None:
        req = RequestContext(
            location=(0.0, 0.0),
            interests=["museum"],
        )
        profile = UserProfile(
            preferences=UserStaticPreferences(interests=["park"]),
        )
        ctx = self.svc.merge(req, profile=profile)
        self.assertCountEqual(ctx.interests, ["museum", "park"])

    def test_merge_avoided_categories_and_places(self) -> None:
        req = RequestContext(
            location=(0.0, 0.0),
            avoided_categories=["fast_food"],
            excluded_place_ids=["10"],
        )
        profile = UserProfile(
            preferences=UserStaticPreferences(avoided_categories=["bar"]),
            history=UserHistory(disliked_place_ids=["20"]),
        )
        ctx = self.svc.merge(req, profile=profile)
        self.assertCountEqual(ctx.avoided_categories, ["fast_food", "bar"])
        self.assertCountEqual(ctx.avoided_place_ids, ["10", "20"])

    # Явные budget_level (int) и pace_mode (str) из запроса маппятся в enum и pace_multiplier.
    def test_merge_budget_and_pace_from_request(self) -> None:
        req = RequestContext(
            location=(54.0, 20.0),
            budget_level=1,
            pace_mode="slow",
        )
        ctx = self.svc.merge(req, None)
        self.assertEqual(ctx.budget_level, BudgetLevel.LOW)
        self.assertEqual(ctx.pace_mode, PaceMode.SLOW)
        self.assertAlmostEqual(ctx.pace_multiplier, 1.3)

    # novelty_mode включается только при достаточной «истории» завершённых маршрутов в профиле.
    def test_merge_novelty_when_enough_completed_routes(self) -> None:
        req = RequestContext(location=(1.0, 1.0))
        profile = UserProfile(behavior=UserBehaviorProfile(completed_routes_count=3))
        ctx = self.svc.merge(req, profile)
        self.assertTrue(ctx.novelty_mode)

    # Режим туриста (is_visiting) увеличивает радиус поиска кандидатов (см. compute_radius в merged_context).
    def test_merge_visiting_expands_radius(self) -> None:
        req = RequestContext(
            location=(1.0, 1.0),
            time_budget_minutes=60,
            is_visiting=True,
        )
        ctx = self.svc.merge(req, None)
        self.assertEqual(ctx.radius_meters, 5000)

    # Без координат и без профиля с home_city_id сервис обязан явно упасть (контракт merge).
    def test_merge_raises_without_location(self) -> None:
        req = RequestContext(location=None)
        with self.assertRaises(ValueError):
            self.svc.merge(req, profile=None)

    # Временная заглушка: home_city_id без координат даёт (0,0) до появления реального lookup городов.
    def test_merge_home_city_placeholder_location(self) -> None:
        req = RequestContext(location=None)
        profile = UserProfile(preferences=UserStaticPreferences(home_city_id="city-1"))
        ctx = self.svc.merge(req, profile=profile)
        self.assertEqual(ctx.location, (0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
