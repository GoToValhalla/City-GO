"""Route preview/build must be bounded (hard deadline) and must return a
structured EMPTY/failed response for 0 or 1 eligible candidates, never a raw
500/502 from an unbounded or under-constrained pipeline."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.candidate_retrieval_service import CandidateRetrievalService
from services.context_merge_service import RequestContext
from services.route_builder_service import RouteBuilderService
from services.user_route_build_service import MAX_BUILD_SECONDS, RouteBuildTimeoutError, UserRouteBuildService


def _make_place(place_id: int, lat: float, lng: float) -> SimpleNamespace:
    return SimpleNamespace(
        id=place_id,
        slug=f"preview-bounded-place-{place_id}",
        title=f"Preview Bounded Place {place_id}",
        short_description=None,
        address="Bounded Street 1",
        lat=lat,
        lng=lng,
        category="cafe",
        outdoor=False,
        indoor=True,
        dog_friendly=False,
        family_friendly=False,
        price_level=1,
        status="active",
        is_active=True,
        opening_hours=None,
        average_visit_duration_minutes=25,
    )


def _request() -> RequestContext:
    return RequestContext(
        location=(54.96, 20.48),
        city_id=None,
        time_budget_minutes=120,
        time_of_day="afternoon",
        interests=[],
        avoided_categories=[],
        excluded_place_ids=[],
        budget_level=None,
        pace_mode=None,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
    )


class TestRoutePreviewZeroAndOneCandidate(unittest.TestCase):
    def test_zero_eligible_places_does_not_crash_new(self) -> None:
        with patch.object(CandidateRetrievalService, "get_candidates", lambda self, db, ctx: []):
            builder = RouteBuilderService()
            result = builder.build_route(db=MagicMock(), request=_request(), profile=None)
            # Must return a structured result object, never raise/crash for zero candidates.
            self.assertIsNotNone(result)
            self.assertEqual(len(result.points), 0)

    def test_one_eligible_place_does_not_crash_new(self) -> None:
        with patch.object(CandidateRetrievalService, "get_candidates", lambda self, db, ctx: [_make_place(1, 54.960, 20.481)]):
            builder = RouteBuilderService()
            result = builder.build_route(db=MagicMock(), request=_request(), profile=None)
            self.assertIsNotNone(result)
            self.assertLessEqual(len(result.points), 1)


class TestRoutePreviewDeadline(unittest.TestCase):
    def test_deadline_guard_raises_timeout_error_new(self) -> None:
        """Simulates elapsed time exceeding MAX_BUILD_SECONDS between pipeline
        stages: the build must raise a distinguishable timeout error instead
        of continuing to run, so callers can map it to a structured response."""
        service = UserRouteBuildService()
        with patch("services.user_route_build_service.time.monotonic", return_value=100.0):
            with self.assertRaises(RouteBuildTimeoutError):
                service._check_deadline(deadline=99.0)

    def test_deadline_not_exceeded_does_not_raise_new(self) -> None:
        service = UserRouteBuildService()
        with patch("services.user_route_build_service.time.monotonic", return_value=1.0):
            service._check_deadline(deadline=MAX_BUILD_SECONDS)  # must not raise


if __name__ == "__main__":
    unittest.main()
