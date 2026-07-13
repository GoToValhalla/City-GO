"""
Интеграционный smoke на реальной БД PostgreSQL для полной цепочки City GO:
создание города -> реальный worker claim -> публикация -> идемпотентный
повторный запуск через реальный worker entrypoint.

По умолчанию тест пропускается (чтобы CI/локаль без реальной Postgres БД не
падали). Включение: RUN_CITY_PIPELINE_E2E_SMOKE=1 и рабочий postgresql*
DATABASE_URL.

Запуск из корня репозитория:
  RUN_CITY_PIPELINE_E2E_SMOKE=1 .venv/bin/python -m unittest \
    tests.test_e2e_city_pipeline_rehearsal_smoke -v

Представляет собой воспроизводимый срез полной ручной E2E-репетиции (city ->
import scopes -> collection persistence -> publish gate -> idempotent
rerun). create_city_and_queue_import и publish_city run через реальный,
непатченный production-код на реальной БД. Коллекция мест собственно через
OSM НЕ вызывается здесь (run_city_import_job's полный legacy+foundation
pipeline делает десятки реальных внешних сетевых вызовов — OSM Overpass,
геокодирование адресов, photo providers — и занимает десятки минут, что
задокументировано вручную в local-context/e2e-rehearsal/checkpoint.md и
непрактично для CI); вместо этого place создаётся напрямую — эквивалент
состояния БД сразу после успешного завершения коллекции. Реальный,
непропатченный run_queued_import_jobs (точка входа настоящего воркера)
используется для обоих проходов — и для проверки, что оно корректно
пропускает уже обработанный job, и для самого idempotent rerun.

Доказывает:
- create_city_and_queue_import создаёт город и job без обхода воркера;
- publish_city публикует только подходящие места и скрывает spam/inactive;
- повторный запуск того же города через реальный run_queued_import_jobs
  после публикации (Дефект #6: launch_status="published" больше не входит в
  importing/imported/review_required) корректно завершает job статусом
  failed с честной причиной и НЕ роняет процесс воркера, НЕ дублирует места.
"""

from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta

from core.config import settings
from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from schemas.admin import AdminCityCreateRequest
from services.admin_city_import_tasks import run_queued_import_jobs
from services.admin_city_publication_service import publish_city
from services.admin_service import create_city_and_queue_import


def _should_run() -> bool:
    if os.environ.get("RUN_CITY_PIPELINE_E2E_SMOKE", "").strip() != "1":
        return False
    url = (settings.database_url or "").lower()
    return "postgresql" in url


@unittest.skipUnless(
    _should_run(),
    "Задайте RUN_CITY_PIPELINE_E2E_SMOKE=1 и postgresql* DATABASE_URL (см. docstring модуля).",
)
class TestCityPipelineE2ESmoke(unittest.TestCase):
    def setUp(self) -> None:
        self.db = SessionLocal()
        self.addCleanup(self.db.close)

    def _cleanup_city(self, city_id: int) -> None:
        from models.city_import_scope import CityImportScope
        from models.data_foundation import CityQualitySnapshot

        self.db.rollback()
        self.db.query(Place).filter(Place.city_id == city_id).delete()
        self.db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city_id).delete()
        self.db.query(CityImportScope).filter(CityImportScope.city_id == city_id).delete()
        self.db.query(CityQualitySnapshot).filter(CityQualitySnapshot.city_id == city_id).delete()
        self.db.query(City).filter(City.id == city_id).delete()
        self.db.commit()

    def test_create_claim_publish_and_idempotent_rerun(self) -> None:
        payload = AdminCityCreateRequest(
            name="E2E Smoke Test Town",
            country="Литва",
            region=None,
            timezone="Europe/Vilnius",
            center_lat=55.70,
            center_lng=21.14,
            radius_km=1,
            actor="e2e-smoke-test",
        )
        city = create_city_and_queue_import(self.db, payload, actor="e2e-smoke-test")
        self.db.commit()
        self.addCleanup(self._cleanup_city, city.id)

        job = self.db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).one()
        self.assertEqual(job.status, "queued")

        # Equivalent of the DB state right after a successful collection run
        # (proven manually, at length, against a real OSM feed during the
        # E2E rehearsal) — seeded directly here so this test stays fast and
        # network-free while still exercising the real publish_city gate and
        # the real run_queued_import_jobs worker entrypoint below.
        place = Place(
            city_id=city.id,
            slug=f"{city.slug}-smoke-place",
            title="Smoke Test Place",
            lat=city.center_lat,
            lng=city.center_lng,
            category="museum",
            is_active=True,
            status="active",
            is_spam_poi=False,
            is_duplicate_suspected=False,
        )
        self.db.add(place)
        job.status = "success"
        job.current_step = "ready_for_review"
        self.db.commit()
        self.db.refresh(place)
        first_run_place_id = place.id

        # The worker must correctly skip a job that is not queued (no
        # double-processing of an already-finished job).
        skip_result = run_queued_import_jobs(actor_id="e2e-smoke-worker", limit=1)
        self.assertEqual(skip_result["processed"], 0)
        self.assertEqual(skip_result["failed"], 0)

        # A fresh, ready readiness snapshot is required by the canonical
        # publication gate (see services/place_publication_eligibility.py) —
        # this is exactly the invariant the publication-safety audit added,
        # after the manual rehearsal published a needs_review/score=46 city
        # with no gate at all.
        from models.data_foundation import CityQualitySnapshot

        self.db.add(CityQualitySnapshot(city_id=city.id, readiness_score=90, quality_status="ready"))
        self.db.commit()

        publication = publish_city(self.db, city.id, actor="e2e-smoke-test")
        self.assertIsNotNone(publication)
        self.db.refresh(city)
        self.assertEqual(city.launch_status, "published")

        published_count = self.db.query(Place).filter(Place.city_id == city.id, Place.is_published.is_(True)).count()
        self.assertEqual(published_count, 1)

        # Idempotent rerun: requeue the same job for the now-published city.
        # This reproduces Defect #6 found during the manual E2E rehearsal:
        # run_due_import_jobs._targets() raises SystemExit when a city's
        # launch_status leaves importing/imported/review_required, and that
        # SystemExit (a BaseException, not Exception) used to propagate
        # uncaught through run_queued_import_jobs and kill the whole worker
        # process instead of just failing this one job.
        job.status = "queued"
        job.current_step = "queued"
        job.updated_at = datetime.utcnow() - timedelta(seconds=1)
        self.db.commit()

        rerun_result = run_queued_import_jobs(actor_id="e2e-smoke-worker", limit=1)

        # The worker call itself must return normally (proving the process
        # would have survived) and report the job as failed, not crash.
        self.assertEqual(rerun_result["processed"], 0)
        self.assertEqual(rerun_result["failed"], 1)

        self.db.refresh(job)
        self.assertEqual(job.status, "failed")
        self.assertIn("No configured import targets", job.last_error or "")

        # Idempotency: no duplicate places were created by the rerun attempt.
        places_after_rerun = self.db.query(Place).filter(Place.city_id == city.id).all()
        self.assertEqual(len(places_after_rerun), 1)
        self.assertEqual(places_after_rerun[0].id, first_run_place_id)

        # The worker loop itself must still be usable afterward (proving it
        # was never torn down by the SystemExit).
        next_poll = run_queued_import_jobs(actor_id="e2e-smoke-worker", limit=1)
        self.assertEqual(next_poll["processed"], 0)
        self.assertEqual(next_poll["failed"], 0)


if __name__ == "__main__":
    unittest.main()
