"""Canonical publication eligibility (services/place_publication_eligibility.py)
— regression coverage for the confirmed spam-POI bypass: bulk publish_place
could publish is_spam_poi=true while city-level publish_city correctly
rejected it. Both paths must now share one eligibility function, and
dry-run/apply must never diverge."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from services.admin_city_publication_service import publish_city
from services.admin_place_bulk_service import apply_bulk, preview_bulk
from services.admin_service import PlacePublicationBlockedError, publish_place
from services.place_publication_eligibility import place_publication_eligibility


def test_spam_poi_rejected_by_place_eligibility_new(db_session: Session, place_factory) -> None:
    place = place_factory(slug="spam-place-eligibility")
    place.is_spam_poi = True
    db_session.commit()

    eligibility = place_publication_eligibility(place)

    assert eligibility.eligible is False
    assert "spam_poi" in eligibility.reasons


def test_spam_poi_rejected_by_city_publication_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="spam-city-publication", is_active=False, launch_status="review_required")
    clean_place = place_factory(city_id=city.id, slug="clean-place", title="Clean Place")
    spam_place = place_factory(city_id=city.id, slug="spam-place", title="Spam Place")
    spam_place.is_spam_poi = True
    db_session.commit()

    result = publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)

    assert result is not None
    db_session.refresh(clean_place)
    db_session.refresh(spam_place)
    assert clean_place.is_published is True
    assert spam_place.is_published is False


def test_spam_poi_rejected_by_bulk_publication_new(db_session: Session, place_factory) -> None:
    """Regression: apply_bulk's 'publish' action used to call publish_place,
    which never checked is_spam_poi, so a spam place could be published
    through the bulk admin action while city-level publish_city correctly
    rejected the same place."""
    place = place_factory(slug="bulk-spam-place", is_published=False, publication_status="needs_review")
    place.is_spam_poi = True
    db_session.commit()

    result = apply_bulk(db_session, [place.id], "publish", {}, actor="test-admin")

    assert result["applied"] == 0
    assert result["failed"] == 1
    assert result["errors"][0]["place_id"] == place.id

    db_session.refresh(place)
    assert place.is_published is False


def test_bulk_publish_directly_blocked_new(db_session: Session, place_factory) -> None:
    place = place_factory(slug="direct-spam-place")
    place.is_spam_poi = True
    db_session.commit()

    with pytest.raises(PlacePublicationBlockedError) as exc_info:
        publish_place(db_session, place.id, actor="test-admin")

    assert "spam_poi" in exc_info.value.failed_gates


def test_dry_run_reports_same_rejection_reason_as_apply_new(db_session: Session, place_factory) -> None:
    """Dry-run (preview_bulk) and apply (apply_bulk) must evaluate the exact
    same target set and reasons — a place preview_bulk marks blocked must
    also be the one apply_bulk actually fails on, with the same reason."""
    ok_place = place_factory(slug="dry-run-ok-place", is_published=False, publication_status="needs_review")
    spam_place = place_factory(slug="dry-run-spam-place", is_published=False, publication_status="needs_review")
    spam_place.is_spam_poi = True
    db_session.commit()

    preview = preview_bulk(db_session, [ok_place.id, spam_place.id], "publish", {})

    assert preview["would_publish_place_ids"] == [ok_place.id]
    assert preview["would_block_place_ids"] == [spam_place.id]
    assert preview["blocked_reasons"][0]["place_id"] == spam_place.id
    assert "spam_poi" in preview["blocked_reasons"][0]["reasons"]

    result = apply_bulk(db_session, [ok_place.id, spam_place.id], "publish", {}, actor="test-admin")

    assert result["applied"] == 1
    assert result["failed"] == 1
    assert result["errors"][0]["place_id"] == spam_place.id

    db_session.refresh(ok_place)
    db_session.refresh(spam_place)
    assert ok_place.is_published is True
    assert spam_place.is_published is False


def test_apply_cannot_exceed_dry_run_approved_set_new(db_session: Session, place_factory) -> None:
    """The set of places apply_bulk actually publishes must be a subset of
    what preview_bulk reported as would_publish_place_ids — apply must never
    publish something dry-run flagged as blocked."""
    places = [
        place_factory(slug=f"subset-place-{i}", is_published=False, publication_status="needs_review")
        for i in range(3)
    ]
    places[1].is_spam_poi = True
    db_session.commit()
    place_ids = [p.id for p in places]

    preview = preview_bulk(db_session, place_ids, "publish", {})
    apply_bulk(db_session, place_ids, "publish", {}, actor="test-admin")

    for place in places:
        db_session.refresh(place)
    actually_published = {p.id for p in places if p.is_published}

    assert actually_published == set(preview["would_publish_place_ids"])
