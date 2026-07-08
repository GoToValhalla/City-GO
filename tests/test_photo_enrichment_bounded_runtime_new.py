"""Photo enrichment finding_images must never run unbounded and must always
write an explicit result — reproduces the prod incident where a Kaliningrad
photo enrichment job stalled 1h41m in finding_images with no final diagnostics."""

from __future__ import annotations

from contextlib import contextmanager

import data.scripts.enrich_place_images as enrich_place_images
from services import admin_city_import_job_service as service


@contextmanager
def _session_from(db_session):
    yield db_session


def test_provider_timeout_does_not_hang_enrichment_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """A provider call that raises (e.g. socket timeout) must not crash the run
    or hang it — it must be caught per-place and recorded as an error, scan continues."""
    city = city_factory(slug="timeout-city")
    place_factory(city_id=city.id, slug="timeout-place", title="Timeout Place", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))

    def raising_fetch(url: str):
        raise TimeoutError("simulated provider timeout")

    monkeypatch.setattr(enrich_place_images, "_fetch_text", raising_fetch)

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert result["scanned_places"] == 1
    assert len(result["errors"]) == 1
    assert "timeout" in result["errors"][0]["error"].lower()


def test_finding_images_run_has_bounded_max_runtime_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """Simulates elapsed time exceeding MAX_RUNTIME_SECONDS mid-scan: the run
    must stop scanning further places, not hang, and mark deadline_exceeded."""
    city = city_factory(slug="deadline-city")
    for i in range(5):
        place_factory(city_id=city.id, slug=f"deadline-place-{i}", title=f"Deadline Place {i}", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))
    monkeypatch.setattr(enrich_place_images, "_collect_candidates_for_place", lambda db, place, city: [])

    call_times = iter([0.0, 0.0, enrich_place_images.MAX_RUNTIME_SECONDS + 1, enrich_place_images.MAX_RUNTIME_SECONDS + 1, enrich_place_images.MAX_RUNTIME_SECONDS + 1, enrich_place_images.MAX_RUNTIME_SECONDS + 1])
    monkeypatch.setattr(enrich_place_images.time, "monotonic", lambda: next(call_times, enrich_place_images.MAX_RUNTIME_SECONDS + 1))

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert result["deadline_exceeded"] is True
    assert result["scanned_places"] < 5
    assert result["provider_status"] == "max_runtime_exceeded"
    assert result["zero_result_reason"] == "max_runtime_exceeded"
    assert any("max runtime" in str(w).lower() for w in result["warnings"])


def test_no_candidates_still_writes_explicit_zero_result_reason_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="no-candidates-city")
    place_factory(city_id=city.id, slug="no-candidates-place", title="No Candidates Place", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))
    monkeypatch.setattr(enrich_place_images, "_collect_candidates_for_place", lambda db, place, city: [])

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert result["created"] == 0
    assert result["candidates_found"] == 0
    assert result["provider_status"] == "source_evidence_exhausted"
    assert result["zero_result_reason"] == "source_evidence_exhausted"


def test_external_provider_error_writes_explicit_error_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="provider-error-city")
    place_factory(city_id=city.id, slug="provider-error-place", title="Provider Error Place", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))

    def raising_collect(db, place, city):
        raise ConnectionError("simulated network failure")

    monkeypatch.setattr(enrich_place_images, "_collect_candidates_for_place", raising_collect)

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert len(result["errors"]) == 1
    assert result["errors"][0]["place_id"] is not None
    assert "network failure" in result["errors"][0]["error"]


def test_partial_scan_writes_scanned_places_before_deadline_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """scanned_places must reflect actual progress made before a deadline stop,
    not zero/None — this is what admin diagnostics reads to show real progress."""
    city = city_factory(slug="partial-scan-city")
    for i in range(4):
        place_factory(city_id=city.id, slug=f"partial-scan-place-{i}", title=f"Partial Scan Place {i}", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))
    monkeypatch.setattr(enrich_place_images, "_collect_candidates_for_place", lambda db, place, city: [])

    call_times = iter([0.0, 0.0, 1.0, 1.0, enrich_place_images.MAX_RUNTIME_SECONDS + 1])
    monkeypatch.setattr(enrich_place_images.time, "monotonic", lambda: next(call_times, enrich_place_images.MAX_RUNTIME_SECONDS + 1))

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert result["scanned_places"] >= 1
    assert result["deadline_exceeded"] is True


def test_created_image_is_committed_incrementally_not_held_in_one_long_transaction_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """Proves progress is committed as it happens (db.commit() called right
    after each created PlaceImage), instead of one uncommitted transaction
    held open for the entire scan — so a crash/kill mid-scan doesn't lose
    everything found so far."""
    from models.place_image import PlaceImage

    city = city_factory(slug="incremental-commit-city")
    place = place_factory(city_id=city.id, slug="incremental-commit-place", title="Incremental Commit Place", image_url=None)
    monkeypatch.setattr(enrich_place_images, "SessionLocal", lambda: _session_from(db_session))
    monkeypatch.setattr(
        enrich_place_images,
        "_collect_candidates_for_place",
        lambda db, place_arg, city_arg: [{"image_url": "https://example.test/photo.jpg", "source_type": "test_source", "source_url": None, "confidence": 0.9, "attribution": None, "license": None}],
    )
    commit_calls: list[int] = []
    original_commit = db_session.commit

    def counting_commit():
        pending_place_images = sum(1 for obj in db_session.new if isinstance(obj, PlaceImage) and obj.place_id == place.id)
        commit_calls.append(pending_place_images)
        return original_commit()

    monkeypatch.setattr(db_session, "commit", counting_commit)

    result = enrich_place_images.run(["--city", city.slug, "--limit", "10", "--apply"])

    assert result["created"] == 1
    assert len(commit_calls) >= 1
    assert commit_calls[0] == 1, "PlaceImage row must be committed right after creation, not deferred to a single end-of-run commit"


def test_admin_photo_diagnostics_exposes_max_runtime_exceeded_reason_new(db_session, city_factory) -> None:
    from services.photo_enrichment_diagnostics import build_photo_enrichment_diagnostics

    city = city_factory(slug="diagnostics-timeout-city")
    run_result = {"deadline_exceeded": True, "scanned_places": 42, "created": 0, "candidates_found": 0, "errors": []}

    diagnostics = build_photo_enrichment_diagnostics(db_session, city, enrichment_result=run_result, scan_limit=100)

    assert diagnostics["provider_status"] == "max_runtime_exceeded"
    assert diagnostics["provider_warning"]
    assert "таймаут" in diagnostics["provider_warning"].lower() or "runtime" in diagnostics["provider_warning"].lower()


def test_run_photo_enrichment_job_marks_success_with_warnings_and_last_error_on_timeout_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    """The admin job wrapper must never report a timed-out run as a clean
    "success" — it must be success_with_warnings with last_error explaining why."""
    city = city_factory(slug="job-timeout-city", launch_status="review_required", is_active=False)
    place_factory(city_id=city.id, slug="job-timeout-place", title="Job Timeout Place", image_url=None)
    timeout_result = {
        "city_slug": city.slug,
        "scanned_places": 3,
        "created": 0,
        "candidates_found": 0,
        "deadline_exceeded": True,
        "provider_status": "max_runtime_exceeded",
        "zero_result_reason": "max_runtime_exceeded",
        "errors": [],
        "warnings": [f"Stopped after exceeding max runtime of {enrich_place_images.MAX_RUNTIME_SECONDS}s; scanned 3 of 500 places."],
        "preview": [],
    }
    monkeypatch.setattr(service, "run_image_enrich", lambda argv: timeout_result)

    job = service.run_photo_enrichment_job(db_session, city_id=city.id, actor_id="test-admin")

    assert job.status == "success_with_warnings"
    assert job.last_error is not None
    assert "таймаут" in job.last_error.lower()
    assert job.step_details["photo_enrichment"]["deadline_exceeded"] is True
    assert job.step_details["photo_diagnostics"]["provider_status"] == "max_runtime_exceeded"
