"""State / boundary tests для recent_runs Data Pipeline."""

from __future__ import annotations

from datetime import datetime, timedelta

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import CityEnrichmentRun
from services.data_pipeline_status.recent_runs import RECENT_LIMIT, build_recent_runs, _trim


def test_error_summary_trim_boundary_240_new() -> None:
    assert _trim("a" * 239) == "a" * 239
    assert _trim("a" * 240) == "a" * 240
    assert _trim("a" * 241) == "a" * 240
    assert _trim(None) is None
    assert _trim("   ") is None


def test_recent_runs_sorted_newest_first_new(db_session, city_factory) -> None:
    city = city_factory(slug="dp-sort", name="Sort")
    older = datetime.utcnow() - timedelta(hours=2)
    newer = datetime.utcnow() - timedelta(minutes=5)
    db_session.add_all(
        [
            CityAdminImportJob(
                city_id=city.id,
                status="completed",
                source="admin_city_import",
                current_step="done",
                started_at=older,
                finished_at=older + timedelta(minutes=1),
                created_at=older,
                updated_at=older,
            ),
            CityEnrichmentRun(
                city_id=city.id,
                run_type="city_enrichment",
                status="completed",
                started_at=newer,
                finished_at=newer + timedelta(minutes=2),
                created_at=newer,
                updated_at=newer,
            ),
        ]
    )
    db_session.commit()
    runs = build_recent_runs(db_session)
    assert runs
    assert runs[0].started_at >= runs[-1].started_at
    assert all(run.run_type_label for run in runs)
    assert all(run.status_label for run in runs)


def test_recent_runs_limit_boundary_new(db_session, city_factory) -> None:
    city = city_factory(slug="dp-limit", name="Limit")
    now = datetime.utcnow()
    for idx in range(RECENT_LIMIT + 5):
        db_session.add(
            CityAdminImportJob(
                city_id=city.id,
                status="queued",
                source="admin_city_import",
                current_step="queued",
                created_at=now - timedelta(minutes=idx),
                updated_at=now,
            )
        )
    db_session.commit()
    runs = build_recent_runs(db_session)
    assert len(runs) <= RECENT_LIMIT
