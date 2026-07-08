"""Server-side safety gates for admin publish/confirm actions, and non-silent
address-refresh/audit-log responses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from models.place import Place
from services.admin_address_job_service import _run_refresh
from services.admin_service import PlacePublicationBlockedError, publish_place
from services.publication_policy import unsafe_manual_publish_gates


def _unsafe_place(db_session, city, **overrides) -> Place:
    defaults = dict(
        city_id=city.id,
        slug="unsafe-place",
        title="Unsafe Place",
        lat=54.7,
        lng=20.5,
        category="cafe",
        confidence=0.0,
        existence_confidence_level="low",
        address=None,
        image_url=None,
        opening_hours=None,
    )
    defaults.update(overrides)
    place = Place(**defaults)
    db_session.add(place)
    db_session.commit()
    db_session.refresh(place)
    return place


def test_unsafe_place_cannot_be_published_without_blocked_reason_new(db_session, city_factory) -> None:
    city = city_factory(slug="unsafe-publish-city")
    place = _unsafe_place(db_session, city)

    try:
        publish_place(db_session, place.id, actor="test-admin")
        assert False, "expected PlacePublicationBlockedError"
    except PlacePublicationBlockedError as exc:
        assert exc.place_id == place.id
        assert exc.blocked_reason == "zero_confidence_missing_critical_fields"

    db_session.refresh(place)
    assert place.is_published is False


def test_confidence_zero_and_missing_fields_blocks_unsafe_action_new(db_session, city_factory) -> None:
    city = city_factory(slug="unsafe-gate-city")
    place = _unsafe_place(db_session, city)

    failed_gates = unsafe_manual_publish_gates(place)

    assert failed_gates == ["zero_confidence_missing_critical_fields"]


def test_freshly_created_place_with_unset_confidence_is_not_blocked_new(db_session, city_factory, place_factory) -> None:
    """A brand-new, not-yet-scored place (confidence is None, the normal default)
    must not be treated the same as an explicitly-scored zero-confidence place."""
    city = city_factory(slug="fresh-place-city")
    place = place_factory(city_id=city.id, slug="fresh-place", title="Fresh Place")

    assert unsafe_manual_publish_gates(place) == []
    published = publish_place(db_session, place.id, actor="test-admin")
    assert published is not None
    assert published.is_published is True


def test_place_with_address_is_not_blocked_even_with_zero_confidence_new(db_session, city_factory) -> None:
    city = city_factory(slug="has-address-city")
    place = _unsafe_place(db_session, city, slug="has-address-place", address="ул. Тестовая, 1")

    assert unsafe_manual_publish_gates(place) == []


def test_address_refresh_reports_explicit_skip_reason_not_silent_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-refresh-city")
    place = place_factory(city_id=city.id, slug="address-refresh-place", address=None)

    from services import admin_address_job_service

    monkeypatch.setattr(admin_address_job_service, "reverse_geocode_payload", lambda lat, lng: {})
    monkeypatch.setattr(admin_address_job_service, "format_nominatim_address", lambda payload: None)

    result = _run_refresh(db_session, city_slug=city.slug, place_ids=[place.id])

    assert result["applied"] == 0
    assert result["skipped"] == 1
    assert len(result["skipped_details"]) == 1
    assert result["skipped_details"][0]["place_id"] == place.id
    assert result["skipped_details"][0]["skip_reason"]
    assert result["skipped_details"][0]["message"]


def test_address_refresh_applies_and_reports_when_geocoding_succeeds_new(db_session, city_factory, place_factory, monkeypatch) -> None:
    city = city_factory(slug="address-refresh-success-city")
    place = place_factory(city_id=city.id, slug="address-refresh-success-place", address=None)

    from services import admin_address_job_service

    monkeypatch.setattr(admin_address_job_service, "reverse_geocode_payload", lambda lat, lng: {"road": "Тестовая", "house_number": "1"})
    monkeypatch.setattr(admin_address_job_service, "format_nominatim_address", lambda payload: "ул. Тестовая, 1")
    monkeypatch.setattr(
        admin_address_job_service,
        "assess_proposed_address",
        lambda address, category, city_name=None, city_slug=None: {"should_apply": True, "confidence": "high"},
    )

    result = _run_refresh(db_session, city_slug=city.slug, place_ids=[place.id])
    db_session.commit()

    assert result["applied"] == 1
    assert result["skipped"] == 0
    db_session.refresh(place)
    assert place.address == "ул. Тестовая, 1"


def test_audit_log_empty_result_includes_applied_filters_and_reason_new(client: TestClient) -> None:
    response = client.get("/admin/audit-log?entity_id=nonexistent-999999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 0
    assert payload["applied_filters"]["entity_id"] == "nonexistent-999999"
    assert payload["empty_reason"]


def test_audit_log_read_does_not_mutate_state_new(client: TestClient, db_session, place_factory) -> None:
    place = place_factory(slug="audit-read-only-place")
    before_status = place.publication_status

    client.get(f"/admin/audit-log?entity_id={place.id}&entity_type=place")

    db_session.refresh(place)
    assert place.publication_status == before_status
