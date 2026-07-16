"""Regression tests for import → snapshot → publication → catalog visibility."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.data_foundation import CityQualitySnapshot
from models.place_publication_decision import PlacePublicationDecision
from services.canonical_publication_guard import (
    assess_place_import_decision,
    evaluate_canonical_publication,
    import_evidence_allows_publish,
)
from services.import_publication_finalize import finalize_import_publication, persist_import_readiness_snapshot
from services.place_service import get_places


def _trusted_place(place_factory, city, **kwargs):
    place = place_factory(city_id=city.id, is_published=False, is_visible_in_catalog=False, publication_status="needs_review", **kwargs)
    place.source = "osm"
    place.confidence = 0.9
    return place


def _ready_snapshot(city_id: int, *, job_id: int) -> CityQualitySnapshot:
    return CityQualitySnapshot(
        city_id=city_id,
        readiness_score=90,
        quality_status="ready",
        snapshot_payload={"import_job_id": job_id, "status": "ready"},
        created_at=datetime.utcnow(),
    )


def test_canonical_guard_auto_publishes_eligible_place_new() -> None:
    from models.place import Place

    place = Place(
        city_id=1,
        title="Cafe",
        category="coffee",
        lat=54.96,
        lng=20.47,
        source="osm",
        confidence=0.9,
        address="Main 1",
        is_active=True,
        status="active",
    )
    decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=decision, evidence_allowed=True)
    assert verdict.outcome == "publish"


def test_canonical_guard_preserves_already_public_place_new(place_factory) -> None:
    place = place_factory(slug="preserve-public", title="Public Cafe", category="coffee")
    decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=decision, evidence_allowed=True)
    assert verdict.outcome == "preserve_public"


def test_import_evidence_blocks_partial_import_new() -> None:
    allowed, reasons = import_evidence_allows_publish(
        job_status="partial_success",
        snapshot_quality_status="ready",
        snapshot_job_id=9,
        current_job_id=9,
    )
    assert allowed is False
    assert "import_status:partial_success" in reasons


def test_import_evidence_blocks_stale_snapshot_job_new() -> None:
    allowed, reasons = import_evidence_allows_publish(
        job_status="success",
        snapshot_quality_status="ready",
        snapshot_job_id=1,
        current_job_id=2,
    )
    assert allowed is False
    assert "snapshot_job_mismatch" in reasons


def test_successful_import_proposes_publication_without_going_live_new(
    db_session: Session,
    city_factory,
    place_factory,
    monkeypatch,
) -> None:
    """Blocker fix: a successful import with fresh, ready evidence must only
    produce a publication PROPOSAL (recorded decision + city marked
    review_required) — it must never call publish_city()/publish_place() or
    set is_published/is_visible_in_catalog/launch_status="published"."""
    city = city_factory(slug="import-publish-city", launch_status="review_required", is_active=False)
    place = _trusted_place(place_factory, city, slug="import-publish-cafe", title="Import Cafe", category="coffee", address="Main 1")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    def fake_recalc(db, *, city_slug, reason, recalculate_place_scores=True):
        snapshot = _ready_snapshot(city.id, job_id=job.id)
        db.add(snapshot)
        city.readiness_score = 90
        city.quality_status = "ready"
        db.commit()
        return {"readiness_score": 90, "status": "ready", "snapshot_id": snapshot.id}

    monkeypatch.setattr("services.import_publication_finalize.recalculate_city_readiness_snapshot", fake_recalc)

    result = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    db_session.refresh(place)
    db_session.refresh(city)

    assert result["status"] == "ready_for_review"
    assert result["city_marked_ready_for_review"] is True
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert city.launch_status == "review_required"
    assert city.is_active is False
    assert get_places(db_session, city_slug=city.slug) == []


def test_partial_import_does_not_publish_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="partial-import-city", launch_status="review_required", is_active=False)
    place = _trusted_place(place_factory, city, slug="partial-cafe", title="Partial Cafe", category="coffee", address="Main 2")
    job = CityAdminImportJob(city_id=city.id, status="partial_success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    result = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="partial_success")
    db_session.refresh(place)

    assert result["status"] == "skipped"
    assert place.is_published is False
    assert get_places(db_session, city_slug=city.slug) == []


def test_stale_snapshot_blocks_publication_new(db_session: Session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="stale-snapshot-city", launch_status="review_required", is_active=False)
    place = _trusted_place(place_factory, city, slug="stale-cafe", title="Stale Cafe", category="coffee", address="Main 3")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    def fake_recalc(db, *, city_slug, reason, recalculate_place_scores=True):
        for existing in db.query(CityQualitySnapshot).filter_by(city_id=city.id).all():
            db.delete(existing)
        snapshot = _ready_snapshot(city.id, job_id=job.id)
        snapshot.created_at = datetime.utcnow() - timedelta(days=40)
        db.add(snapshot)
        db.commit()
        return {"readiness_score": 90, "status": "ready"}

    monkeypatch.setattr("services.import_publication_finalize.recalculate_city_readiness_snapshot", fake_recalc)

    result = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    db_session.refresh(place)

    assert result["status"] == "failed"
    assert "stale_readiness_snapshot" in result.get("reasons", [])
    assert place.is_published is False


def test_rejected_place_stays_invisible_new(db_session: Session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="reject-city", launch_status="review_required", is_active=False)
    place = _trusted_place(place_factory, city, slug="reject-cafe", title="", category="coffee")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        "services.import_publication_finalize.recalculate_city_readiness_snapshot",
        lambda db, *, city_slug, reason, recalculate_place_scores=True: {"status": "ready"},
    )
    db_session.add(_ready_snapshot(city.id, job_id=job.id))
    db_session.commit()

    result = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    db_session.refresh(place)

    assert result["status"] == "failed"
    assert place.is_published is False
    assert place.publication_status in {"archived", "needs_review", "hidden"}


def test_finalize_is_idempotent_new(db_session: Session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="idempotent-city", launch_status="review_required", is_active=False)
    place = _trusted_place(place_factory, city, slug="idempotent-cafe", title="Idempotent Cafe", category="park")
    job = CityAdminImportJob(city_id=city.id, status="success", source="admin_city_import")
    db_session.add(job)
    db_session.commit()

    def fake_recalc(db, *, city_slug, reason, recalculate_place_scores=True):
        snapshot = _ready_snapshot(city.id, job_id=job.id)
        db.add(snapshot)
        city.readiness_score = 90
        city.quality_status = "ready"
        db.commit()
        return {"status": "ready"}

    monkeypatch.setattr("services.import_publication_finalize.recalculate_city_readiness_snapshot", fake_recalc)

    first = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    second = finalize_import_publication(db_session, city=city, job=job, place_ids=[place.id], import_status="success")
    db_session.refresh(place)
    decisions = db_session.query(PlacePublicationDecision).filter_by(place_id=place.id).count()

    assert first["status"] == "ready_for_review"
    assert second["status"] == "ready_for_review"
    assert decisions >= 2
    assert place.is_published is False


def test_published_place_survives_import_review_mark_new(db_session: Session, place_factory) -> None:
    from services.place_import_lifecycle_service import mark_place_for_review

    place = place_factory(slug="survive-review", title="Survive Review", category="coffee")
    mark_place_for_review(place, reason="import_or_enrichment_changed")
    db_session.commit()

    assert place.is_published is True
    assert place.is_visible_in_catalog is True
