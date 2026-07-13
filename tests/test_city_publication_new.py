from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models.data_foundation import CityQualitySnapshot
from services.admin_city_publication_service import preview_city_publication, publish_city
from services.place_service import get_places


def _snapshot(city_id: int, *, quality_status: str, created_at: datetime | None = None) -> CityQualitySnapshot:
    return CityQualitySnapshot(
        city_id=city_id,
        readiness_score=90 if quality_status == "ready" else 40,
        quality_status=quality_status,
        created_at=created_at or datetime.utcnow(),
    )


def test_publish_city_publishes_only_public_safe_places_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="review-city", name="Review City", is_active=False, launch_status="review_required")
    cafe = place_factory(city_id=city.id, slug="review-cafe", title="Review Cafe", category="cafe")
    pharmacy = place_factory(city_id=city.id, slug="review-pharmacy", title="Review Pharmacy", category="health")

    # This test targets place-level eligibility (place category safety gate),
    # not the city readiness gate, so bypass the readiness gate explicitly —
    # see test_publish_city_blocked_without_readiness_snapshot_new below for
    # the readiness gate's own coverage.
    result = publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)

    assert result is not None
    assert result.city.launch_status == "published"
    assert result.city.is_active is True
    assert result.places_total == 2
    assert result.places_published == 1
    assert result.places_hidden == 1

    db_session.refresh(cafe)
    db_session.refresh(pharmacy)
    assert cafe.is_published is True
    assert cafe.is_visible_in_catalog is True
    assert cafe.is_route_eligible is True
    assert pharmacy.is_published is False
    assert pharmacy.is_visible_in_catalog is False
    assert pharmacy.is_route_eligible is False


def test_publish_city_requires_at_least_one_public_place_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="empty-public-city", name="Empty Public City", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="only-pharmacy", title="Only Pharmacy", category="health")

    with pytest.raises(ValueError):
        publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)

    db_session.refresh(city)
    assert city.launch_status == "review_required"
    assert city.is_active is False


def test_public_places_require_published_city_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="hidden-city", name="Hidden City", is_active=False, launch_status="review_required")
    place = place_factory(city_id=city.id, slug="hidden-cafe", title="Hidden Cafe", category="cafe")
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.is_route_eligible = True
    db_session.commit()

    assert get_places(db_session, city_slug=city.slug) == []

    publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)

    visible = get_places(db_session, city_slug=city.slug)
    assert [item.slug for item in visible] == ["hidden-cafe"]


def test_publish_city_blocked_without_readiness_snapshot_new(db_session: Session, city_factory, place_factory) -> None:
    """Regression: the E2E rehearsal published a city with
    readiness_score=46/quality_status=needs_review because publish_city had
    no readiness/snapshot check at all. A missing snapshot must now block
    publication (Snapshot Freshness + Publication Safety invariants)."""
    city = city_factory(slug="no-snapshot-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="no-snapshot-place", title="No Snapshot Place")

    with pytest.raises(ValueError, match="readiness gate"):
        publish_city(db_session, city.id, actor="test-admin")

    db_session.refresh(city)
    assert city.launch_status == "review_required"
    assert city.is_active is False


def test_publish_city_blocked_when_quality_status_needs_review_new(db_session: Session, city_factory, place_factory) -> None:
    """needs_review must not auto-publish — only quality_status='ready' does,
    per the canonical policy, unless an explicit override is passed."""
    city = city_factory(slug="needs-review-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="needs-review-place", title="Needs Review Place")
    db_session.add(_snapshot(city.id, quality_status="needs_review"))
    db_session.commit()

    with pytest.raises(ValueError, match="quality_status_not_ready"):
        publish_city(db_session, city.id, actor="test-admin")


def test_publish_city_blocked_with_stale_snapshot_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="stale-snapshot-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="stale-snapshot-place", title="Stale Snapshot Place")
    stale_at = datetime.utcnow() - timedelta(days=40)
    db_session.add(_snapshot(city.id, quality_status="ready", created_at=stale_at))
    db_session.commit()

    with pytest.raises(ValueError, match="stale_readiness_snapshot"):
        publish_city(db_session, city.id, actor="test-admin")


def test_publish_city_allowed_with_fresh_ready_snapshot_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="ready-snapshot-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="ready-snapshot-place", title="Ready Snapshot Place")
    db_session.add(_snapshot(city.id, quality_status="ready"))
    db_session.commit()

    result = publish_city(db_session, city.id, actor="test-admin")

    assert result is not None
    assert result.city.launch_status == "published"


def test_publish_city_explicit_override_bypasses_readiness_gate_new(db_session: Session, city_factory, place_factory) -> None:
    """An explicit, audited override is the only allowed way to publish
    without a passing readiness gate — never a silent default."""
    city = city_factory(slug="override-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="override-place", title="Override Place")

    result = publish_city(db_session, city.id, actor="test-admin", override_readiness_gate=True)

    assert result is not None
    assert result.city.launch_status == "published"


def test_preview_city_publication_matches_publish_city_new(db_session: Session, city_factory, place_factory) -> None:
    """Dry-run and apply must evaluate the same target set and reasons."""
    city = city_factory(slug="preview-matches-city", is_active=False, launch_status="review_required")
    cafe = place_factory(city_id=city.id, slug="preview-cafe", title="Preview Cafe", category="cafe")
    pharmacy = place_factory(city_id=city.id, slug="preview-pharmacy", title="Preview Pharmacy", category="health")
    db_session.add(_snapshot(city.id, quality_status="ready"))
    db_session.commit()

    preview = preview_city_publication(db_session, city.id)
    assert preview is not None
    assert preview.gate_allowed is True
    assert list(preview.would_publish_place_ids) == [cafe.id]
    assert list(preview.would_hide_place_ids) == [pharmacy.id]

    result = publish_city(db_session, city.id, actor="test-admin")

    db_session.refresh(cafe)
    db_session.refresh(pharmacy)
    assert cafe.is_published is True
    assert pharmacy.is_published is False
    assert result.places_published == len(preview.would_publish_place_ids)
    assert result.places_hidden == len(preview.would_hide_place_ids)
