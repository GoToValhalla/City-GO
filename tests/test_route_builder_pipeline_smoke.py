"""
E2E smoke: RouteBuilderService.build_route без реального PostGIS-запроса.

Подменяется только STEP 2 (get_candidates) синтетическими объектами с полями как у Place;
merge → hard_filters → scoring → assembly → time_aware → finalize — реальный код.

Кандидаты — SimpleNamespace (не ORM Place()), чтобы не триггерить configure_mappers()
и ошибку связей City↔places в тестовом окружении.

Запуск (нужны зависимости из requirements.txt; проект ориентирован на Python 3.10+):
  python3.11 -m unittest tests.test_route_builder_pipeline_smoke -v

С pytest (если установлен):
  python3.11 -m pytest tests/test_route_builder_pipeline_smoke.py -v
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services.candidate_retrieval_service import CandidateRetrievalService
from services.context_merge_service import RequestContext
from services.route_builder_service import RouteBuilderService
from services.route_finalize_service import FinalRoute


def _make_place(place_id: int, lat: float, lng: float) -> SimpleNamespace:
    """Минимальный duck-typing контракт для шагов pipeline (атрибуты как у Place)."""
    return SimpleNamespace(
        id=place_id,
        slug=f"smoke-place-{place_id}",
        title=f"Smoke Place {place_id}",
        short_description=None,
        address="Smoke Street 1",
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


def _fake_get_candidates(self, db, ctx):  # noqa: ARG002 — сигнатура как у оригинала
    return [
        _make_place(1, 54.960, 20.481),
        _make_place(2, 54.961, 20.482),
        _make_place(3, 54.962, 20.483),
    ]


class TestRouteBuilderPipelineSmoke(unittest.TestCase):
    def test_build_route_e2e_smoke(self) -> None:
        with patch.object(CandidateRetrievalService, "get_candidates", _fake_get_candidates):
            builder = RouteBuilderService()
            db = MagicMock()

            request = RequestContext(
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

            result = builder.build_route(db=db, request=request, profile=None)

            self.assertIsInstance(result, FinalRoute)
            self.assertGreaterEqual(result.total_places, 1)
            self.assertTrue(getattr(result, "pipeline_trace", []))
            self.assertGreaterEqual(len(result.points), 1)
            for point in result.points:
                self.assertIsNotNone(point.lat)
                self.assertIsNotNone(point.lng)
                self.assertGreater(point.visit_minutes, 0)
                self.assertTrue(point.title.startswith("Smoke Place"))
                self.assertEqual(point.address, "Smoke Street 1")

if __name__ == "__main__":
    unittest.main()
