"""Regression tests: a published Place must never be destructively modified
by an automatic process (import, enrichment, address recovery, photo
recovery, backfills, taxonomy normalization).

services/place_change_review_service.py::propose_place_change() is the
shared guard: when a place is currently published, proposed field values
are stored as a `place_change` ReviewQueueItem candidate instead of being
written to the live row. Approval applies the candidate; rejection is a
true no-op since the live row was never touched.
"""
from __future__ import annotations

from models.review_queue_item import ReviewQueueItem
from services.place_change_review_service import (
    PLACE_CHANGE_FIELD,
    approve_place_change_review,
    propose_place_change,
    reject_place_change_review,
)


def test_propose_place_change_does_not_touch_published_place_new(db_session, place_factory) -> None:
    place = place_factory(title="Original Title", address="Original Address")
    assert place.is_published is True

    applied = propose_place_change(
        db_session,
        place=place,
        proposed={"title": "New Title", "address": "New Address"},
        reason="import_reimport",
    )

    assert applied is False
    assert place.title == "Original Title"
    assert place.address == "Original Address"
    assert place.is_published is True


def test_propose_place_change_creates_reviewable_candidate_new(db_session, place_factory) -> None:
    place = place_factory(title="Original Title")

    propose_place_change(db_session, place=place, proposed={"title": "New Title"}, reason="import_reimport")
    db_session.commit()

    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()
    assert item is not None
    assert item.status == "open"
    assert item.payload["applied"] is False
    assert item.payload["changes"]["title"] == {"before": "Original Title", "after": "New Title"}


def test_propose_place_change_passes_through_for_unpublished_place_new(db_session, place_factory) -> None:
    place = place_factory(title="Draft Title", is_published=False, is_active=True, publication_status="draft")

    applied = propose_place_change(db_session, place=place, proposed={"title": "New Title"}, reason="import")

    assert applied is True
    # Caller is responsible for actually writing the field once True is returned.
    assert place.title == "Draft Title"


def test_repeated_import_preserves_published_place_new(db_session, place_factory) -> None:
    """A second/third automatic write attempt with the same proposal must
    keep re-queuing the same open candidate rather than ever touching the
    live published row."""
    place = place_factory(title="Original Title", category="cafe")

    for _ in range(3):
        applied = propose_place_change(db_session, place=place, proposed={"title": "Reimported Title"}, reason="import_reimport")
        db_session.commit()
        assert applied is False

    assert place.title == "Original Title"
    assert place.is_published is True
    items = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD, status="open").all()
    assert len(items) == 1


def test_enrichment_preserves_published_place_new(db_session, place_factory) -> None:
    """Photo/address-style enrichment must not overwrite a published place's
    content directly — mirrors the enrich_place_images.py wiring."""
    place = place_factory(title="Cafe", image_url=None, address="Real Street 12")

    applied = propose_place_change(db_session, place=place, proposed={"image_url": "https://example.com/photo.jpg"}, reason="photo_enrichment_candidate")
    db_session.commit()

    assert applied is False
    assert place.image_url is None
    assert place.is_published is True


def test_partial_failed_import_preserves_published_place_new(db_session, place_factory) -> None:
    """If the automatic process crashes after proposing but before an admin
    ever resolves the review, the published place is exactly as before —
    there is no partially-applied state to roll back."""
    place = place_factory(title="Original Title", address="Original Address")

    try:
        propose_place_change(db_session, place=place, proposed={"title": "Partial Title"}, reason="import_reimport")
        db_session.commit()
        raise RuntimeError("simulated mid-import crash")
    except RuntimeError:
        db_session.rollback()

    db_session.refresh(place)
    assert place.title == "Original Title"
    assert place.address == "Original Address"
    assert place.is_published is True


def test_approved_review_publishes_the_candidate_new(db_session, place_factory) -> None:
    place = place_factory(title="Original Title", category="cafe")
    propose_place_change(db_session, place=place, proposed={"title": "Approved Title"}, reason="import_reimport")
    db_session.commit()
    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()

    result = approve_place_change_review(db_session, item.id, actor="qa-admin")
    db_session.commit()
    db_session.refresh(place)

    assert result is not None
    assert place.title == "Approved Title"
    assert place.is_published is True


def test_rejected_review_keeps_the_existing_public_version_new(db_session, place_factory) -> None:
    place = place_factory(title="Original Title", category="cafe")
    propose_place_change(db_session, place=place, proposed={"title": "Rejected Title"}, reason="import_reimport")
    db_session.commit()
    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()

    result = reject_place_change_review(db_session, item.id, actor="qa-admin")
    db_session.commit()
    db_session.refresh(place)

    assert result is not None
    assert place.title == "Original Title"
    assert place.is_published is True


def test_propose_place_change_lineage_via_import_job_id_new(db_session, place_factory, city_factory) -> None:
    """Every proposed change carries explicit lineage to the import job that
    produced it (ReviewQueueItem.job_id), not a timestamp heuristic."""
    from models.city_admin_import_job import CityAdminImportJob

    city = city_factory(slug="lineage-city")
    place = place_factory(title="Original Title", city_id=city.id)
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import")
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    propose_place_change(db_session, place=place, proposed={"title": "New Title"}, reason="import_reimport", job_id=job.id)
    db_session.commit()

    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()
    assert item.job_id == job.id


def test_category_normalization_preserves_published_place_category_new(db_session, place_factory, category_factory) -> None:
    """services/category_normalize_service.py must route through the same
    guard rather than overwriting a published place's category directly.

    "cafe" normalizes to canonical "coffee" (core/place_category_hierarchy.py),
    so this exercises the real write path rather than a no-op skip."""
    from services.category_normalize_service import normalize_places_categories

    category_factory(code="coffee", name="Coffee")
    place = place_factory(title="Old Cafe", category="cafe")

    normalize_places_categories(db_session, places=[place], apply=True)
    db_session.commit()

    assert place.category == "cafe"
    assert place.is_published is True
    item = db_session.query(ReviewQueueItem).filter_by(place_id=place.id, field_name=PLACE_CHANGE_FIELD).first()
    assert item is not None
    assert item.payload["changes"]["category"] == {"before": "cafe", "after": "coffee"}
