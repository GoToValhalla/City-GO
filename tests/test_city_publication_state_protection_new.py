"""Regression tests for the "published city never auto-unpublishes" invariant.

Root cause covered here: SQLAlchemy expires ORM attributes after every
db.commit(). Any automatic process that commits and later reassigns
City.launch_status / City.is_active without re-reading them first makes the
`set` event fire with oldvalue=NO_VALUE instead of the real "published"
value, which silently defeated the publication guard in models/city.py.
Repeated imports, enrichment-only pipeline runs and lifecycle writes all
commit repeatedly before touching these fields, so this was reachable in
production (observed for Arkhangelsk).
"""
from __future__ import annotations

from models.city import allow_city_product_state_change
from models.city_admin_import_job import CityAdminImportJob


def _publish(city_factory, **overrides):
    defaults = dict(slug="published-city", name="Published City", is_active=True, launch_status="published")
    defaults.update(overrides)
    return city_factory(**defaults)


def test_expired_attribute_set_does_not_bypass_guard_new(db_session, city_factory) -> None:
    city = _publish(city_factory, slug="expire-guard")
    # Multiple commits expire the in-memory attribute before the next write,
    # which is exactly the shape of the real import/enrichment pipelines.
    db_session.commit()
    db_session.commit()
    db_session.commit()

    city.launch_status = "review_required"
    db_session.commit()
    db_session.refresh(city)

    assert city.launch_status == "published"


def test_repeated_import_keeps_published_city_published_new(db_session, city_factory, monkeypatch) -> None:
    from services import admin_city_import_job_service as job_service

    city = _publish(city_factory, slug="import-repeat")

    def fake_collection(db, *, job, city, actor_id, force=True, notify_completion=True):
        return {"import": {"places_saved": 3}, "changed_place_ids": []}

    def fake_source_enrichment(**kwargs):
        return {"source_enrichment": "skipped"}

    monkeypatch.setattr(job_service, "run_enrichment_pipeline", fake_collection)
    monkeypatch.setattr(job_service, "run_foundation_pipeline", fake_source_enrichment)
    monkeypatch.setattr(job_service, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 90})

    job_service.run_city_import_job(db_session, city_id=city.id, actor_id="qa")
    db_session.refresh(city)

    assert city.launch_status == "published"
    assert city.is_active is True


def test_enrichment_only_pipeline_keeps_published_city_published_new(db_session, city_factory, monkeypatch) -> None:
    from services.import_pipeline import enrichment_only as mod

    city = _publish(city_factory, slug="enrichment-only-repeat")
    job = CityAdminImportJob(city_id=city.id, status="queued", source="admin_city_enrichment")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    monkeypatch.setattr(mod, "_run_address_batches", lambda slug, heartbeat=None: {"checked": 0, "updated": 0, "errors": 0, "batches": 0, "last_scanned_place_id": 0})
    monkeypatch.setattr(mod, "_run_image_batches", lambda slug, heartbeat=None: {"scanned_places": 0, "created": 0, "errors": [], "batches": 0, "last_scanned_place_id": 0})
    monkeypatch.setattr(mod, "normalize_city_categories", lambda db, *, city_slug, apply=True, job_id=None: {"scanned": 0, "updated": 0})
    monkeypatch.setattr(mod, "run_quality_cleanup", lambda argv: {"updated": 0})
    monkeypatch.setattr(mod, "compute_city_readiness", lambda db, *, city_slug: {"readiness_score": 90})
    monkeypatch.setattr(mod, "send_admin_alert", lambda **kwargs: {"sent": True})

    mod.run_enrichment_only_pipeline(db_session, job=job, city=city, actor_id="qa")
    db_session.refresh(city)

    assert city.launch_status == "published"
    assert city.is_active is True


def test_review_does_not_change_city_publication_state_new(db_session, city_factory, place_factory) -> None:
    from models.review_queue_item import ReviewQueueItem
    from services.place_change_review_service import PLACE_CHANGE_FIELD, approve_place_change_review

    city = _publish(city_factory, slug="review-noop")
    place = place_factory(city_id=city.id, slug="review-noop-place", title="Review Noop Place", category="cafe")
    item = ReviewQueueItem(
        city_id=city.id,
        place_id=place.id,
        field_name=PLACE_CHANGE_FIELD,
        reason="critical_field_changed",
        status="open",
        payload={"changes": {}},
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    result = approve_place_change_review(db_session, item.id, actor="qa")
    assert result is not None

    db_session.refresh(city)
    assert city.launch_status == "published"
    assert city.is_active is True


def test_publication_policy_does_not_change_city_publication_state_new(db_session, city_factory, place_factory) -> None:
    from services.publication_policy import evaluate_new_place

    city = _publish(city_factory, slug="policy-noop")
    place = place_factory(city_id=city.id, slug="policy-noop-place", title="Policy Noop Place", category="cafe")

    evaluate_new_place(place, city=city)
    db_session.refresh(city)

    assert city.launch_status == "published"
    assert city.is_active is True


def test_automatic_unpublish_is_impossible_without_guard_flag_new(db_session, city_factory) -> None:
    city = _publish(city_factory, slug="no-auto-unpublish")
    db_session.commit()

    city.launch_status = "unpublished"
    city.is_active = False
    db_session.commit()
    db_session.refresh(city)

    assert city.launch_status == "published"
    assert city.is_active is True


def test_admin_publish_and_unpublish_still_work_new(db_session, city_factory, place_factory) -> None:
    from services.admin_city_publication_service import publish_city, unpublish_city

    city = city_factory(slug="admin-flow-city", name="Admin Flow City", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="admin-flow-place", title="Admin Flow Place", category="cafe")

    published = publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)
    assert published is not None
    assert published.city.launch_status == "published"
    assert published.city.is_active is True

    unpublished = unpublish_city(db_session, city.id, actor="test-admin", reason="qa regression")
    assert unpublished is not None
    assert unpublished.city.launch_status == "unpublished"
    assert unpublished.city.is_active is False


def test_allow_city_product_state_change_flag_still_bypasses_guard_new(db_session, city_factory) -> None:
    city = _publish(city_factory, slug="explicit-admin-bypass")
    db_session.commit()

    allow_city_product_state_change(city)
    city.launch_status = "unpublished"
    city.is_active = False
    db_session.commit()
    db_session.refresh(city)

    assert city.launch_status == "unpublished"
    assert city.is_active is False
