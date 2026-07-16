"""Repository-level regression: no import, enrichment, worker, finalize, or
background-job code path may call the live publication writers
(publish_city, publish_place, or apply_canonical_publication_verdict with
record_only=False/omitted). Only explicit, authenticated admin actions
(services/admin_service.py, services/admin_city_publication_service.py,
reached exclusively through routers/admin*.py) may ever flip
is_active/is_published/is_visible_in_catalog/launch_status="published".

This is a source-text scan, deliberately: it proves the absence of a call
at the exact places the blocker names, and would fail loudly the moment
someone re-introduces one, rather than relying on runtime coverage alone.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Every source-level entrypoint or shared module that runs unattended as
# part of import, enrichment, or a background job/worker — the exact set
# named or implied by "any caller that invokes publish_city() automatically
# after import success".
UNATTENDED_PIPELINE_FILES = (
    "services/import_publication_finalize.py",
    "services/import_pipeline_publication.py",
    "services/import_pipeline_foundation.py",
    "services/import_pipeline_foundation_steps.py",
    "services/import_pipeline/enrichment_only.py",
    "services/admin_city_import_job_service.py",
    "services/admin_city_import_runner.py",
    "services/place_import_lifecycle_service.py",
    "data/scripts/import_city_osm.py",
    "data/scripts/import_city_osm_v2.py",
    "data/scripts/run_admin_import_worker.py",
    "data/scripts/run_due_import_jobs.py",
    "data/scripts/run_city_enrichment_pipeline.py",
    "data/scripts/cleanup_imported_places_quality.py",
)

# The only two modules allowed to actually mutate live publication/visibility
# flags — the canonical admin writers.
ADMIN_WRITER_MODULES = (
    "services/admin_service.py",
    "services/admin_city_publication_service.py",
    "services/canonical_publication_apply.py",
)

FORBIDDEN_LIVE_PUBLISH_CALLS = ("publish_city", "publish_place")


def _source(path: str) -> str:
    full = REPO_ROOT / path
    assert full.exists(), f"expected pipeline file missing: {path}"
    return full.read_text(encoding="utf-8")


def _call_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def test_no_unattended_path_calls_live_publish_writer_new():
    for path in UNATTENDED_PIPELINE_FILES:
        source = _source(path)
        called = _call_names(source)
        for forbidden in FORBIDDEN_LIVE_PUBLISH_CALLS:
            assert forbidden not in called, (
                f"{path} must never call {forbidden}() — only explicit admin "
                f"actions in {ADMIN_WRITER_MODULES} may publish/unpublish"
            )


def test_apply_canonical_publication_verdict_import_call_sites_use_record_only_new():
    """Every import-side caller of apply_canonical_publication_verdict must
    pass record_only=True — the flag that blocks auto-publish
    (_set_published) at the writer itself."""
    import_call_sites = (
        "services/import_pipeline_publication.py",
        "services/import_publication_finalize.py",
    )
    for path in import_call_sites:
        source = _source(path)
        assert "apply_canonical_publication_verdict(" in source, f"{path} should call the canonical writer"
        assert "record_only=True" in source, (
            f"{path} must call apply_canonical_publication_verdict with record_only=True"
        )


def test_finalize_import_publication_does_not_set_launch_status_published_new():
    """The city-level equivalent of the same invariant: finalize may only
    move launch_status to the existing review_required workflow marker,
    never to "published" directly."""
    source = _source("services/import_publication_finalize.py")
    assert 'launch_status = "published"' not in source
    assert 'launch_status = CITY_STATUS_PUBLISHED' not in source


def test_finalize_import_publication_runtime_never_publishes_new(db_session, city_factory, place_factory, monkeypatch):
    """Behavioral counterpart to the source scans above: actually run
    finalize_import_publication with fresh, ready evidence and assert
    nothing went live."""
    from datetime import datetime

    from models.city_admin_import_job import CityAdminImportJob
    from models.data_foundation import CityQualitySnapshot
    from services.import_publication_finalize import finalize_import_publication

    city = city_factory(slug="no-unattended-publish-city", launch_status="review_required", is_active=False)
    place = place_factory(
        city_id=city.id, slug="no-unattended-publish-place", category="coffee", address="Main 1",
        is_published=False, is_visible_in_catalog=False, publication_status="needs_review",
    )
    place.source = "osm"
    place.confidence = 0.9
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    def fake_recalc(db, *, city_slug, reason, recalculate_place_scores=True):
        snapshot = CityQualitySnapshot(
            city_id=city.id, readiness_score=90, quality_status="ready",
            snapshot_payload={"import_job_id": job.id, "status": "ready"}, created_at=datetime.utcnow(),
        )
        db.add(snapshot)
        db.commit()
        return {"status": "ready"}

    monkeypatch.setattr("services.import_publication_finalize.recalculate_city_readiness_snapshot", fake_recalc)

    finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    db_session.refresh(place)
    db_session.refresh(city)

    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert city.is_active is False
    assert city.launch_status != "published"
