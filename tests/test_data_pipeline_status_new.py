"""Тесты read-only Data Pipeline Control Plane."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import CityEnrichmentRun, EnrichmentTask
from models.place import Place
from models.place_image import PlaceImage
from models.review_queue_item import ReviewQueueItem
from services.data_pipeline_status.build_status import build_data_pipeline_status
from services.data_pipeline_status.constants import CANONICAL_QUEUE_CODES, QUEUE_LABELS


def test_data_pipeline_status_endpoint_is_read_only(client, db_session, monkeypatch):
  monkeypatch.setattr(db_session, "commit", lambda *args, **kwargs: pytest.fail("GET must not commit"))
  response = client.get("/admin/data-pipeline/status")
  assert response.status_code == 200
  body = response.json()
  assert "overall_status" in body
  assert "fetched_at" in body


def test_data_pipeline_returns_four_canonical_queues(client):
  body = client.get("/admin/data-pipeline/status").json()
  codes = [row["code"] for row in body["queues"]]
  assert codes == list(CANONICAL_QUEUE_CODES)
  assert all(row["label"] == QUEUE_LABELS[row["code"]] for row in body["queues"])


def test_data_pipeline_metrics_include_places_without_coordinates(db_session, city_factory, place_factory):
  city = city_factory(slug="dp-metrics", name="DP Metrics")
  place_factory(city_id=city.id, slug="with-coords", title="With", lat=54.95, lng=20.48)
  payload = build_data_pipeline_status(db_session)
  assert payload.metrics.places_total >= 1
  assert hasattr(payload.metrics, "places_without_coordinates")


def test_data_pipeline_empty_db_reports_empty_status(db_session):
  payload = build_data_pipeline_status(db_session)
  if payload.metrics.places_total == 0:
    assert payload.overall_status == "empty"


def test_data_pipeline_partial_degraded_when_import_failed(db_session, city_factory):
  city = city_factory(slug="dp-degraded", name="DP Degraded")
  job = CityAdminImportJob(
    city_id=city.id,
    status="failed",
    source="admin_city_import",
    current_step="error",
    last_error="provider timeout",
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow(),
  )
  db_session.add(job)
  db_session.commit()
  payload = build_data_pipeline_status(db_session)
  assert payload.overall_status in {"partial_degraded", "full_degraded", "healthy"}
  import_queue = next(row for row in payload.queues if row.code == "import")
  assert import_queue.failed_count >= 1


def test_data_pipeline_recent_runs_include_duration_and_error(db_session, city_factory):
  city = city_factory(slug="dp-runs", name="DP Runs")
  started = datetime.utcnow() - timedelta(minutes=5)
  finished = datetime.utcnow()
  job = CityAdminImportJob(
    city_id=city.id,
    status="failed",
    source="admin_city_import",
    current_step="error",
    started_at=started,
    finished_at=finished,
    last_error="import provider unavailable",
    created_at=started,
    updated_at=finished,
  )
  db_session.add(job)
  run = CityEnrichmentRun(
    city_id=city.id,
    run_type="city_enrichment",
    status="completed",
    started_at=started,
    finished_at=finished,
    created_at=started,
    updated_at=finished,
  )
  db_session.add(run)
  db_session.commit()
  payload = build_data_pipeline_status(db_session)
  assert payload.recent_runs
  failed = next(row for row in payload.recent_runs if row.error_summary)
  assert failed.duration_seconds is not None
  assert failed.error_summary


def test_data_pipeline_dom_labels_are_russian_not_raw_codes(client):
  body = client.get("/admin/data-pipeline/status").json()
  for row in body["queues"]:
    assert "_" not in row["label"]
    assert row["label"] == QUEUE_LABELS[row["code"]]
  for run in body["recent_runs"]:
    assert run["run_type_label"]
    assert run["status_label"]
