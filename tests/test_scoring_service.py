"""
Юнит-тесты для services.scoring_service.ScoringService (новая логика breakdown и весов).

Запуск:
  python3.11 -m unittest tests.test_scoring_service -v
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.scoring_service import ScoringService


def _base_ctx(**overrides) -> MergedContext:
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


def _place(**kwargs) -> SimpleNamespace:
    defaults = {
        "id": 1,
        "slug": "t",
        "title": "T",
        "short_description": None,
        "address": None,
        "lat": 55.0,
        "lng": 20.0,
        "category": "cafe",
        "outdoor": False,
        "indoor": True,
        "dog_friendly": False,
        "family_friendly": False,
        "price_level": 2,
        "opening_hours": None,
        "average_visit_duration_minutes": 30,
        "confidence": "medium",
        "last_verified_at": None,
        "source_url": None,
        "image_url": None,
        "wikidata_id": None,
        "osm_id": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestScoringServiceInterest(unittest.TestCase):
    def test_interest_neutral_when_no_interests(self) -> None:
        svc = ScoringService()
        p = _place(category="museum")
        ctx = _base_ctx(interests=[])
        self.assertEqual(svc._interest_score(p, ctx), 0.5)

    def test_interest_exact_casefold(self) -> None:
        svc = ScoringService()
        p = _place(category="Cafe")
        ctx = _base_ctx(interests=["cafe"])
        self.assertEqual(svc._interest_score(p, ctx), 1.0)

    def test_interest_multi_category_string(self) -> None:
        svc = ScoringService()
        p = _place(category="park, walk")
        ctx = _base_ctx(interests=["walk"])
        self.assertEqual(svc._interest_score(p, ctx), 1.0)

    def test_interest_soft_substring(self) -> None:
        svc = ScoringService()
        p = _place(category="walking")
        ctx = _base_ctx(interests=["walk"])
        self.assertEqual(svc._interest_score(p, ctx), 0.72)

    def test_interest_empty_category_with_interests(self) -> None:
        svc = ScoringService()
        p = _place(category=None)
        ctx = _base_ctx(interests=["cafe"])
        self.assertEqual(svc._interest_score(p, ctx), 0.22)

    def test_interest_russian_architecture_maps_to_culture(self) -> None:
        svc = ScoringService()
        p = _place(category="culture")
        ctx = _base_ctx(interests=["архитектура"])
        self.assertEqual(svc._interest_score(p, ctx), 1.0)

    def test_interest_nature_maps_to_park(self) -> None:
        svc = ScoringService()
        p = _place(category="park")
        ctx = _base_ctx(interests=["природа"])
        self.assertEqual(svc._interest_score(p, ctx), 1.0)


class TestScoringServiceDistance(unittest.TestCase):
    def test_distance_zero_lat_is_valid(self) -> None:
        svc = ScoringService()
        p = _place(lat=0.0, lng=20.0)
        ctx = _base_ctx(location=(0.0, 20.0), radius_meters=111_000)
        self.assertAlmostEqual(svc._distance_score(p, ctx), 1.0, places=5)

    def test_distance_none_coords_zero_score(self) -> None:
        svc = ScoringService()
        p = _place(lat=None, lng=20.0)
        ctx = _base_ctx()
        self.assertEqual(svc._distance_score(p, ctx), 0.0)

    def test_distance_further_is_lower(self) -> None:
        svc = ScoringService()
        close = _place(lat=55.0, lng=20.0)
        far = _place(lat=55.05, lng=20.05)
        ctx = _base_ctx(location=(55.0, 20.0), radius_meters=1500)
        self.assertGreater(svc._distance_score(close, ctx), svc._distance_score(far, ctx))


class TestScoringServicePriceBudget(unittest.TestCase):
    def test_price_fits_budget(self) -> None:
        svc = ScoringService()
        p = _place(price_level=1)
        ctx = _base_ctx(budget_level=BudgetLevel.HIGH)
        self.assertGreaterEqual(svc._price_budget_score(p, ctx), 0.82)

    def test_price_above_budget_penalized(self) -> None:
        svc = ScoringService()
        p = _place(price_level=3)
        ctx = _base_ctx(budget_level=BudgetLevel.LOW)
        self.assertLess(svc._price_budget_score(p, ctx), 0.5)

    def test_price_none_neutral_band(self) -> None:
        svc = ScoringService()
        p = _place(price_level=None)
        ctx = _base_ctx()
        self.assertEqual(svc._price_budget_score(p, ctx), 0.58)


class TestScoringServiceNovelty(unittest.TestCase):
    def test_novelty_mode_on(self) -> None:
        svc = ScoringService()
        ctx = _base_ctx(novelty_mode=True)
        self.assertEqual(svc._novelty_score(_place(), ctx), 1.0)

    def test_novelty_mode_off(self) -> None:
        svc = ScoringService()
        ctx = _base_ctx(novelty_mode=False)
        self.assertEqual(svc._novelty_score(_place(), ctx), 0.32)


class TestScoringServiceContextWithHoursPatch(unittest.TestCase):
    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_context_visiting_outdoor_boost(self, _mock_open) -> None:
        svc = ScoringService()
        p = _place(outdoor=True, indoor=False, opening_hours=None)
        ctx = _base_ctx(is_visiting=True, pace_mode=PaceMode.NORMAL)
        self.assertGreaterEqual(svc._context_score(p, ctx), 0.52 + 0.16)

    @patch("services.scoring_service.is_place_open_at", return_value=True)
    def test_context_open_now_soft_boost(self, _mock_open) -> None:
        svc = ScoringService()
        p = _place(
            outdoor=False,
            indoor=True,
            opening_hours={"mon": {"open": "09:00", "close": "21:00"}},
        )
        ctx = _base_ctx(is_visiting=False, pace_mode=PaceMode.NORMAL)
        score = svc._context_score(p, ctx)
        self.assertGreater(score, 0.6)


class TestScoringServiceScoreIntegration(unittest.TestCase):
    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_score_sorts_by_final_score(self, _mock) -> None:
        svc = ScoringService()
        ctx = _base_ctx(
            interests=["cafe"],
            location=(55.0, 20.0),
            radius_meters=2000,
            budget_level=BudgetLevel.HIGH,
        )
        worse = _place(id=1, slug="a", title="A", lat=55.1, lng=20.1, category="museum")
        better = _place(id=2, slug="b", title="B", lat=55.001, lng=20.001, category="cafe")
        out = svc.score([worse, better], ctx)
        self.assertEqual(out[0].place.id, 2)
        self.assertGreater(out[0].score, out[1].score)

    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_breakdown_has_expected_keys(self, _mock) -> None:
        svc = ScoringService()
        ctx = _base_ctx(interests=["cafe"])
        out = svc.score([_place()], ctx)[0]
        self.assertEqual(
            set(out.breakdown.keys()),
            {
                "base_quality",
                "interest",
                "distance",
                "context",
                "popularity",
                "novelty",
                "data_quality",
                "time_context",
                "data_confidence",
                "popularity_proxy",
                "personalization",
            },
        )

    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_time_context_evening_boosts_bar_over_morning(self, _mock) -> None:
        svc = ScoringService()
        place = _place(category="bar")
        morning = svc.score([place], _base_ctx(time_of_day="morning"))[0]
        evening = svc.score([place], _base_ctx(time_of_day="evening"))[0]
        self.assertLess(morning.breakdown["time_context"], evening.breakdown["time_context"])
        self.assertLess(morning.score, evening.score)

    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_data_confidence_low_scores_below_high(self, _mock) -> None:
        svc = ScoringService()
        low = _place(id=1, confidence="low")
        high = _place(id=2, confidence="high")
        scored = svc.score([low, high], _base_ctx())
        self.assertEqual(scored[0].place.id, 2)
        self.assertGreater(scored[0].breakdown["data_confidence"], scored[1].breakdown["data_confidence"])


class TestScoringServiceDataQuality(unittest.TestCase):
    """Проверка влияния place.validation['issues'] на breakdown и итоговый score."""

    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_validation_issues_lower_final_score_than_identical_clean_place(self, _mock) -> None:
        svc = ScoringService()
        ctx = _base_ctx(
            interests=["cafe"],
            location=(55.0, 20.0),
            radius_meters=2000,
            budget_level=BudgetLevel.MID,
        )
        clean = _place(id=10, slug="clean", title="Clean")
        dirty = _place(id=11, slug="dirty", title="Dirty")
        dirty.validation = {"is_valid": False, "issues": ["category_empty"]}

        scored_clean = svc.score([clean], ctx)[0]
        scored_dirty = svc.score([dirty], ctx)[0]

        self.assertIn("data_quality", scored_clean.breakdown)
        self.assertEqual(scored_clean.breakdown["data_quality"], 1.0)
        self.assertLess(scored_dirty.breakdown["data_quality"], scored_clean.breakdown["data_quality"])
        self.assertLess(scored_dirty.score, scored_clean.score)

    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_two_validation_issues_lower_score_than_one_issue(self, _mock) -> None:
        svc = ScoringService()
        ctx = _base_ctx(
            interests=["cafe"],
            location=(55.0, 20.0),
            radius_meters=2000,
            budget_level=BudgetLevel.MID,
        )
        one = _place(id=20, slug="one", title="One")
        one.validation = {"is_valid": False, "issues": ["category_empty"]}
        two = _place(id=21, slug="two", title="Two")
        two.validation = {
            "is_valid": False,
            "issues": ["category_empty", "price_level_out_of_range"],
        }

        s_one = svc.score([one], ctx)[0]
        s_two = svc.score([two], ctx)[0]

        self.assertLess(s_two.breakdown["data_quality"], s_one.breakdown["data_quality"])
        self.assertLess(s_two.score, s_one.score)


class TestScoringServicePersonalization(unittest.TestCase):
    @patch("services.scoring_service.is_place_open_at", return_value=None)
    def test_personalization_boosts_liked_place(self, _mock) -> None:
        svc = ScoringService()
        ctx = _base_ctx(liked_place_ids=["2"])
        liked = _place(id=2, slug="liked")
        neutral = _place(id=3, slug="neutral")
        scored = svc.score([neutral, liked], ctx)
        self.assertEqual(scored[0].place.id, 2)
        self.assertGreater(scored[0].breakdown["personalization"], scored[1].breakdown["personalization"])


if __name__ == "__main__":
    unittest.main()
