"""Интеграционная матрица Data Pipeline: seed → build_status → контракт."""

from __future__ import annotations

from datetime import datetime

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import EnrichmentTask
from models.review_queue_item import ReviewQueueItem
from services.data_pipeline_status.build_status import build_data_pipeline_status


def _seed_import_jobs(db_session, city_id: int, count: int) -> None:
    now = datetime.utcnow()
    for _ in range(count):
        db_session.add(
            CityAdminImportJob(
                city_id=city_id,
                status="queued",
                source="admin_city_import",
                current_step="queued",
                created_at=now,
                updated_at=now,
            )
        )


def test_import_queue_boundary_10_ok_11_warning_new(db_session, city_factory) -> None:
    city = city_factory(slug="dp-boundary", name="Boundary")
    _seed_import_jobs(db_session, city.id, 10)
    db_session.commit()
    payload_10 = build_data_pipeline_status(db_session)
    import_10 = next(row for row in payload_10.queues if row.code == "import")
    assert import_10.pending_count == 10
    assert import_10.status == "ok"

    _seed_import_jobs(db_session, city.id, 1)
    db_session.commit()
    payload_11 = build_data_pipeline_status(db_session)
    import_11 = next(row for row in payload_11.queues if row.code == "import")
    assert import_11.pending_count == 11
    assert import_11.status == "warning"


def test_full_degraded_when_three_sections_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="dp-full", name="Full degraded")
    place = place_factory(city_id=city.id, slug="dp-place")
    now = datetime.utcnow()
    db_session.add(
        CityAdminImportJob(
            city_id=city.id,
            status="failed",
            source="admin_city_import",
            current_step="error",
            last_error="timeout",
            created_at=now,
            updated_at=now,
        )
    )
    for _ in range(11):
        db_session.add(
            EnrichmentTask(city_id=city.id, task_type="enrich_place", status="queued")
        )
    db_session.add(
        ReviewQueueItem(
            city_id=city.id,
            place_id=place.id,
            field_name="title",
            reason="needs_review",
            status="open",
        )
    )
    db_session.commit()
    payload = build_data_pipeline_status(db_session)
    assert payload.overall_status == "full_degraded"
    assert len(payload.degraded_sections) >= 3
