"""Address enrichment (backfill) must never run unbounded and must always
write an explicit result — mirrors the same class of fix already applied to
photo enrichment (data/scripts/enrich_place_images.py MAX_RUNTIME_SECONDS)."""

from __future__ import annotations

import services.place_address_backfill as place_address_backfill
from services import admin_city_import_job_service as service


def test_provider_timeout_does_not_hang_address_enrichment_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-timeout-city")
    place_factory(city_id=city.id, slug="address-timeout-place", title="Address Timeout Place", address=None)

    def raising_resolve(place):
        raise TimeoutError("simulated geocode timeout")

    monkeypatch.setattr(place_address_backfill, "_resolve_candidate", raising_resolve)

    result = place_address_backfill.run_backfill(db_session, city_slug=city.slug, limit=10, sleep_seconds=0, apply=True)

    assert result["checked"] == 1
    assert result["errors"] == 1


def test_max_runtime_deadline_stops_address_backfill_scan_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-deadline-city")
    for i in range(5):
        place_factory(city_id=city.id, slug=f"address-deadline-place-{i}", title=f"Address Deadline Place {i}", address=None)
    monkeypatch.setattr(place_address_backfill, "_resolve_candidate", lambda place: None)

    call_times = iter([0.0, 0.0, place_address_backfill.MAX_RUNTIME_SECONDS + 1, place_address_backfill.MAX_RUNTIME_SECONDS + 1, place_address_backfill.MAX_RUNTIME_SECONDS + 1, place_address_backfill.MAX_RUNTIME_SECONDS + 1])
    monkeypatch.setattr(place_address_backfill.time, "monotonic", lambda: next(call_times, place_address_backfill.MAX_RUNTIME_SECONDS + 1))

    result = place_address_backfill.run_backfill(db_session, city_slug=city.slug, limit=10, sleep_seconds=0, apply=True)

    assert result["deadline_exceeded"] is True
    assert result["checked"] < 5
    assert any("max runtime" in str(w).lower() for w in result["warnings"])


def test_partial_scan_writes_checked_places_before_deadline_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-partial-scan-city")
    for i in range(4):
        place_factory(city_id=city.id, slug=f"address-partial-place-{i}", title=f"Address Partial Place {i}", address=None)
    monkeypatch.setattr(place_address_backfill, "_resolve_candidate", lambda place: None)

    call_times = iter([0.0, 0.0, 1.0, 1.0, place_address_backfill.MAX_RUNTIME_SECONDS + 1])
    monkeypatch.setattr(place_address_backfill.time, "monotonic", lambda: next(call_times, place_address_backfill.MAX_RUNTIME_SECONDS + 1))

    result = place_address_backfill.run_backfill(db_session, city_slug=city.slug, limit=10, sleep_seconds=0, apply=True)

    assert result["checked"] >= 1
    assert result["deadline_exceeded"] is True


def test_no_address_result_has_explicit_reason_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-no-result-city")
    place_factory(city_id=city.id, slug="address-no-result-place", title="Address No Result Place", address=None)
    monkeypatch.setattr(place_address_backfill, "_resolve_candidate", lambda place: None)

    result = place_address_backfill.run_backfill(db_session, city_slug=city.slug, limit=10, sleep_seconds=0, apply=False)

    assert result["updated"] == 0
    assert result["skipped_generic_result"] == 1
    assert result["results"][0]["status"] == "skipped_generic"


def test_external_provider_error_visible_in_admin_diagnostics_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """The admin job wrapper must never report a timed-out backfill as a clean
    "success" — it must be success_with_warnings with last_error explaining why."""
    city = city_factory(slug="address-job-timeout-city", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="address-job-timeout-place", title="Address Job Timeout Place", address=None)
    timeout_result = {
        "mode": "apply",
        "city": city.slug,
        "checked": 3,
        "updated": 0,
        "errors": 0,
        "deadline_exceeded": True,
        "warnings": [f"Stopped after exceeding max runtime of {place_address_backfill.MAX_RUNTIME_SECONDS}s; checked 3 places."],
        "results": [],
        "updated_place_ids": [],
    }
    monkeypatch.setattr(service, "run_address_backfill", lambda argv: timeout_result)

    queued = service.queue_city_import_job(db_session, city_id=city.id, actor_id="test-admin")
    db_session.commit()
    claimed = service.claim_queued_job(db_session, job_id=queued.id, worker_id="test-worker", actor_id="test-admin")
    job = service.run_address_enrichment_job(db_session, city_id=city.id, actor_id="test-admin", job_id=claimed.id)

    assert job.status == "success_with_warnings"
    assert job.last_error is not None
    assert "таймаут" in job.last_error.lower()
    assert job.step_details["address_enrichment"]["deadline_exceeded"] is True
