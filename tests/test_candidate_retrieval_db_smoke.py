"""
Интеграционный smoke только для STEP 2: CandidateRetrievalService.get_candidates
на реальной БД PostgreSQL.

По умолчанию тест пропускается (чтобы CI/локаль без БД не падали).
Включение: RUN_CANDIDATE_RETRIEVAL_DB_SMOKE=1 и рабочий DATABASE_URL в .env / окружении.

Запуск из корня репозитория:
  RUN_CANDIDATE_RETRIEVAL_DB_SMOKE=1 python3.11 -m unittest tests.test_candidate_retrieval_db_smoke -v

Доказывает: запрос из candidate_retrieval_service выполняется без исключения
(драйвер, SQL, portable distance expression, маппинг Place); пустой список допустим,
если в радиусе нет строк.
"""

from __future__ import annotations

import os
import unittest

from core.config import settings
from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.candidate_retrieval_service import CandidateRetrievalService
from services.context_merge_service import ContextMergeService, RequestContext


_ORM_CONTEXT = (
    Category,
    City,
    Collection,
    CollectionPlace,
    PlaceSchedule,
    PlaceTag,
    Route,
    RoutePlace,
    Tag,
)


def _should_run() -> bool:
    if os.environ.get("RUN_CANDIDATE_RETRIEVAL_DB_SMOKE", "").strip() != "1":
        return False
    url = (settings.database_url or "").lower()
    return "postgresql" in url


@unittest.skipUnless(
    _should_run(),
    "Задайте RUN_CANDIDATE_RETRIEVAL_DB_SMOKE=1 и postgresql* DATABASE_URL (см. docstring модуля).",
)
class TestCandidateRetrievalDbSmoke(unittest.TestCase):
    def test_get_candidates_real_db(self) -> None:
        merge = ContextMergeService()
        request = RequestContext(
            location=(54.96, 20.48),
            city_id=None,
            time_budget_minutes=120,
            interests=[],
            avoided_categories=[],
            excluded_place_ids=[],
            budget_level=None,
            pace_mode=None,
            is_visiting=False,
            visit_city_id=None,
            visit_days=1,
        )
        ctx = merge.merge(request, profile=None)

        db = SessionLocal()
        try:
            svc = CandidateRetrievalService()
            candidates = svc.get_candidates(db, ctx)
        finally:
            db.close()

        self.assertIsInstance(candidates, list)
        for p in candidates:
            self.assertIsInstance(p, Place)
            self.assertIsNotNone(p.id)
