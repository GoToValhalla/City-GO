from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_payload import SNAPSHOT_KEY, build_import_job_payload
from services.admin_extended_service import get_admin_import_job, list_admin_import_jobs

ROOT = Path(__file__).resolve().parents[1]


def test_admin_get_routes_do_not_default_to_refresh_true():
    offenders = []
    for path in (ROOT / "routers").glob("admin*.py"):
        text = path.read_text(encoding="utf-8")
        if "@router.get" in text and ("refresh: bool = True" in text or "refresh=True" in text):
            offenders.append(path.relative_to(ROOT).as_posix())
    assert offenders == []


def test_admin_coverage_gaps_get_is_snapshot_only():
    text = (ROOT / "routers" / "admin_coverage_gaps.py").read_text(encoding="utf-8")
    get_block = text.split('@router.get("/cities/{city_slug}")')[0]
    list_block = get_block.split('@router.get("")', 1)[1]
    assert "run_data_coverage_assurance" not in list_block
    assert "db.commit" not in list_block


def _job(db_session, *, city_id: int, status: str, source: str = "admin_city_import", current_step: str = "queued", created_at: datetime | None = None, step_details: dict[str, object] | None = None) -> CityAdminImportJob:
    now = created_at or datetime.utcnow()
    job = CityAdminImportJob(city_id=city_id, status=status, source=source, current_step=current_step, created_at=now, updated_at=now, started_at=now if status == "running" else None, step_details=step_details or {})
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


def _snapshot(job: CityAdminImportJob, city_slug: str) -> dict[str, object]:
    return {
        "version": 1,
        "source": "test",
        "taken_at": datetime.utcnow().isoformat(),
        "city_id": job.city_id,
        "city_slug": city_slug,
        "job_id": job.id,
        "data_coverage": {"places_total": 1, "places_published": 1, "places_unpublished": 0, "without_address": 0, "without_photo": 1, "without_description": 0, "address_coverage_pct": 100.0, "photo_coverage_pct": 0.0, "description_coverage_pct": 100.0, "pending_photos": 0},
        "change_summary": {"job_id": job.id, "city_id": job.city_id, "city_slug": city_slug, "created": 0, "updated": 0, "unchanged": 0, "rejected": 0, "hidden": 0, "needs_review": 0, "total_changes": 0},
    }


def test_get_import_jobs_is_read_only_and_does_not_mutate_stale_running_jobs(client, db_session, city_factory, place_factory, monkeypatch):
    city = city_factory(slug="readonly-list", name="Read Only List", launch_status="importing", is_active=False)
    place_factory(city_id=city.id, slug="readonly-list-place", title="Read Only Place")
    job = _job(db_session, city_id=city.id, status="running", current_step="importing", created_at=datetime.utcnow() - timedelta(hours=3))

    from services import admin_city_import_job_payload as payload_module
    from services import admin_extended_service as extended_module

    monkeypatch.setattr(payload_module, "recover_failed_import_with_places", lambda *args, **kwargs: pytest.fail("GET /admin/import-jobs must not recover failed imports"))
    monkeypatch.setattr(payload_module, "normalize_reviewable_import_state", lambda *args, **kwargs: pytest.fail("GET /admin/import-jobs must not normalize import state"))
    monkeypatch.setattr(extended_module, "_mark_stalled_imports_before_read", lambda *args, **kwargs: pytest.fail("GET /admin/import-jobs must not mark stalled jobs"))
    monkeypatch.setattr(db_session, "commit", lambda *args, **kwargs: pytest.fail("GET /admin/import-jobs must not commit"))

    response = client.get("/admin/import-jobs")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["city_id"] == city.id for item in body["items"])
    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "running"
    assert job.current_step == "importing"
    assert city.launch_status == "importing"
    assert city.is_active is False


def test_get_import_job_detail_is_read_only_and_keeps_latest_enrichment_for_snapshot(client, db_session, city_factory, place_factory, monkeypatch):
    city = city_factory(slug="readonly-detail", name="Read Only Detail", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="readonly-detail-place", title="Read Only Detail Place", image_url=None)
    base = datetime.utcnow() - timedelta(minutes=10)
    photo = _job(db_session, city_id=city.id, status="success", source="admin_photo_enrichment", current_step="snapshot_refresh", created_at=base, step_details={"photo_enrichment": {"created": 0, "scanned_places": 5, "candidates_found": 0, "provider_status": "source_evidence_exhausted", "errors": []}})
    _job(db_session, city_id=city.id, status="success", source="admin_address_enrichment", current_step="snapshot_refresh", created_at=base + timedelta(minutes=1), step_details={"address_enrichment": {"updated": 2, "scanned_places": 3}})
    snapshot_job = _job(db_session, city_id=city.id, status="success", source="admin_snapshot_refresh", current_step="snapshot_ready", created_at=base + timedelta(minutes=2))
    snapshot_job.step_details = {SNAPSHOT_KEY: _snapshot(snapshot_job, city.slug)}
    db_session.commit()

    from services import admin_city_import_job_payload as payload_module

    monkeypatch.setattr(payload_module, "recover_failed_import_with_places", lambda *args, **kwargs: pytest.fail("GET detail must not recover failed imports"))
    monkeypatch.setattr(payload_module, "normalize_reviewable_import_state", lambda *args, **kwargs: pytest.fail("GET detail must not normalize import state"))
    monkeypatch.setattr(db_session, "commit", lambda *args, **kwargs: pytest.fail("GET detail must not commit"))

    response = client.get(f"/admin/import-jobs/{city.id}")

    assert response.status_code == 200
    body = response.json()
    details = body["step_details"]
    assert body["source"] == "admin_snapshot_refresh"
    assert details["latest_photo_enrichment"]["job_id"] == photo.id
    assert details["latest_photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
    assert details["photo_enrichment"]["provider_status"] == "source_evidence_exhausted"
    assert details["latest_address_enrichment"]["updated"] == 2
    db_session.refresh(snapshot_job)
    db_session.refresh(city)
    assert snapshot_job.status == "success"
    assert city.launch_status == "review_required"


def test_active_state_backend_uses_status_not_current_step(db_session, city_factory, place_factory):
    legacy_city = city_factory(slug="legacy-success", name="Legacy Success", launch_status="review_required", is_active=False)
    place_factory(city_id=legacy_city.id, slug="legacy-success-place", title="Legacy Success Place")
    legacy_job = _job(db_session, city_id=legacy_city.id, status="success", current_step="queued")
    legacy_job.step_details = {SNAPSHOT_KEY: _snapshot(legacy_job, legacy_city.slug)}
    db_session.commit()

    payload = build_import_job_payload(db_session, legacy_city)
    assert payload["status"] == "success"
    assert payload["status_group"] == "review"
    assert payload["auto_refresh_seconds"] is None
    assert payload["can_retry"] is True
    assert payload["can_cancel"] is False
    assert payload["can_publish"] is True

    legacy_job.current_step = "snapshot_refresh"
    db_session.commit()
    payload = get_admin_import_job(db_session, legacy_city.id)
    assert payload is not None
    assert payload["status"] == "success"
    assert payload["auto_refresh_seconds"] is None
    assert payload["can_retry"] is True
    assert payload["can_cancel"] is False
    assert payload["status_group"] == "review"

    published_city = city_factory(slug="published-running", name="Published Running", launch_status="published", is_active=True)
    place_factory(city_id=published_city.id, slug="published-running-place", title="Published Running Place")
    running_job = _job(db_session, city_id=published_city.id, status="running", current_step="snapshot_refresh")
    running_job.step_details = {SNAPSHOT_KEY: _snapshot(running_job, published_city.slug)}
    db_session.commit()
    row = next(item for item in list_admin_import_jobs(db_session, limit=50, offset=0)["items"] if item["city_id"] == published_city.id)
    assert row["status"] == "running"
    assert row["launch_status"] == "published"
    assert row["status_group"] == "running"
    assert row["auto_refresh_seconds"] == 7
    assert row["can_cancel"] is True


def test_import_queue_get_is_read_only_and_mark_stalled_is_explicit_write(client, db_session, city_factory, monkeypatch):
    city = city_factory(slug="queue-readonly", name="Queue Read Only", launch_status="importing", is_active=False)
    job = _job(db_session, city_id=city.id, status="running", source="admin_photo_enrichment", current_step="finding_images", created_at=datetime.utcnow() - timedelta(hours=3))

    from routers import admin_import_queue as queue_router

    monkeypatch.setattr(queue_router, "send_admin_alert", lambda *args, **kwargs: None)
    get_response = client.get("/admin/import-queue")
    assert get_response.status_code == 200
    queue = get_response.json()
    assert queue["running"] == 1
    assert queue["stalled_running"] == 1
    assert queue["by_source"] == {"admin_photo_enrichment": 1}
    assert job.id in queue["stale_job_ids"]
    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "running"
    assert city.launch_status == "importing"

    post_response = client.post("/admin/import-queue/mark-stalled")
    assert post_response.status_code == 200
    body = post_response.json()
    assert body["marked"] == 1
    assert body["job_ids"] == [job.id]
    db_session.refresh(job)
    db_session.refresh(city)
    assert job.status == "stalled"
    assert job.current_step == "error"
    assert city.launch_status == "import_failed"
