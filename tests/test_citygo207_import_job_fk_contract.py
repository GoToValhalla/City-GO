from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.review_queue_item import ReviewQueueItem
from services.import_pipeline import runner as import_runner
from services.import_pipeline.steps import STEP_COLLECTING_PLACES
from services.review_queue_service import ReviewQueueJobLinkError, ensure_review_item


def _create_import_job(db_session: Session, *, city_id: int, status: str = "queued") -> CityAdminImportJob:
    """Create a persisted CityAdminImportJob so review_queue_items.job_id can reference it."""
    job = CityAdminImportJob(city_id=city_id, status=status)
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def test_review_queue_item_accepts_city_admin_import_job_id(
    db_session: Session,
    city_factory: Callable[..., Any],
    place_factory: Callable[..., Any],
) -> None:
    """review_queue_items.job_id must point to city_admin_import_jobs.id, not batch/city/external ids."""
    city = city_factory(slug="review-fk-city", name="Review FK City")
    job = _create_import_job(db_session, city_id=city.id)
    place = place_factory(city_id=city.id, slug="review-fk-place", title="Review FK Place", publication_status="needs_review")

    item = ensure_review_item(
        db_session,
        city_id=city.id,
        place_id=place.id,
        job_id=job.id,
        field_name="publication_status",
        reason="import_data_changed",
    )
    db_session.flush()

    assert item.job_id == job.id
    stored = db_session.query(ReviewQueueItem).filter(ReviewQueueItem.id == item.id).one()
    assert stored.job_id == job.id


def test_review_queue_item_rejects_unknown_job_id_before_fk_flush(
    db_session: Session,
    city_factory: Callable[..., Any],
    place_factory: Callable[..., Any],
) -> None:
    """Invalid job_id fails with a product error before the database FK explodes."""
    city = city_factory(slug="review-fk-invalid-city", name="Review FK Invalid City")
    place = place_factory(city_id=city.id, slug="review-fk-invalid-place", title="Review FK Invalid Place")

    with pytest.raises(ReviewQueueJobLinkError, match="city_admin_import_jobs.id=999999 does not exist"):
        ensure_review_item(
            db_session,
            city_id=city.id,
            place_id=place.id,
            job_id=999999,
            field_name="publication_status",
            reason="import_data_changed",
        )


def test_collecting_places_step_forwards_city_admin_import_job_id(
    db_session: Session,
    city_factory: Callable[..., Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The collecting_places OSM stage must receive CityAdminImportJob.id as context."""
    city = city_factory(slug="collecting-places-city", name="Collecting Places City")
    # status="running" — run_enrichment_pipeline is called here directly,
    # simulating the row exactly as its real caller (run_city_import_job,
    # after claim_queued_job) would hand it off.
    job = _create_import_job(db_session, city_id=city.id, status="running")
    captured: dict[str, Any] = {}

    def fake_run_osm_import_only(city_slug: str, *, force: bool = True, city_admin_import_job_id: int | None = None) -> dict[str, Any]:
        captured["city_slug"] = city_slug
        captured["force"] = force
        captured["city_admin_import_job_id"] = city_admin_import_job_id
        raise RuntimeError("stop after collecting_places contract capture")

    monkeypatch.setattr(import_runner, "run_osm_import_only", fake_run_osm_import_only)

    with pytest.raises(RuntimeError, match="stop after collecting_places contract capture"):
        import_runner.run_enrichment_pipeline(
            db_session,
            job=job,
            city=city,
            actor_id="test-admin",
            notify_completion=False,
        )

    db_session.refresh(job)
    assert captured == {
        "city_slug": city.slug,
        "force": True,
        "city_admin_import_job_id": job.id,
    }
    assert job.current_step == STEP_COLLECTING_PLACES
    # run_enrichment_pipeline no longer writes job.status (see its own
    # comment) — with total<=0 it re-raises instead, and the caller
    # (run_city_import_job) is the one that applies a terminal _transition;
    # called directly here, job.status stays exactly what it was handed.
    assert job.status == "running"
    assert "stop after collecting_places contract capture" in (job.last_error or "")
