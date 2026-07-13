"""Readiness-override lockdown: until a separate authorization model exists,
no normal admin API/UI request may bypass the city publication readiness
gate. override_readiness_gate is a service-only parameter on publish_city()
(services/admin_city_publication_service.py) for tests/internal emergency
use via direct Python calls — it is intentionally NOT part of any public
request schema, and the POST /admin/import-jobs/{city_id}/publish endpoint
never forwards a client-controlled value for it."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from models.data_foundation import CityQualitySnapshot
from schemas.admin import AdminCityPublishRequest
from services.admin_city_publication_service import publish_city


def test_public_request_schema_has_no_override_field_new() -> None:
    """The field must not exist on the schema at all — not just default to
    False — so no amount of client payload can set it."""
    assert "override_readiness_gate" not in AdminCityPublishRequest.model_fields


def test_extra_payload_field_is_silently_dropped_by_schema_new() -> None:
    request = AdminCityPublishRequest.model_validate(
        {"reason": "test", "override_readiness_gate": True}
    )
    assert not hasattr(request, "override_readiness_gate")


def test_normal_api_publish_request_cannot_override_readiness_gate_new(
    client: TestClient, db_session, city_factory, place_factory,
) -> None:
    """A needs_review city with a fresh snapshot must return HTTP 409 even
    when the request body tries to smuggle override_readiness_gate=true —
    the router must never read or forward that field."""
    city = city_factory(slug="lockdown-needs-review-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place", title="Lockdown Place")
    db_session.add(CityQualitySnapshot(city_id=city.id, readiness_score=40, quality_status="needs_review"))
    db_session.commit()

    response = client.post(
        f"/admin/import-jobs/{city.id}/publish",
        json={"reason": "trying to bypass", "override_readiness_gate": True},
    )

    assert response.status_code == 409
    assert "readiness gate" in response.json()["detail"]
    db_session.refresh(city)
    assert city.launch_status == "review_required"
    assert city.is_active is False


def test_needs_review_city_receives_409_new(client: TestClient, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="lockdown-needs-review-only-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place-2", title="Lockdown Place 2")
    db_session.add(CityQualitySnapshot(city_id=city.id, readiness_score=50, quality_status="needs_review"))
    db_session.commit()

    response = client.post(f"/admin/import-jobs/{city.id}/publish", json={})

    assert response.status_code == 409
    assert "quality_status_not_ready" in response.json()["detail"]


def test_missing_snapshot_receives_409_new(client: TestClient, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="lockdown-missing-snapshot-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place-3", title="Lockdown Place 3")
    db_session.commit()

    response = client.post(f"/admin/import-jobs/{city.id}/publish", json={})

    assert response.status_code == 409
    assert "missing_readiness_snapshot" in response.json()["detail"]


def test_stale_snapshot_receives_409_new(client: TestClient, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="lockdown-stale-snapshot-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place-4", title="Lockdown Place 4")
    stale_at = datetime.utcnow() - timedelta(days=40)
    db_session.add(CityQualitySnapshot(city_id=city.id, readiness_score=90, quality_status="ready", created_at=stale_at))
    db_session.commit()

    response = client.post(f"/admin/import-jobs/{city.id}/publish", json={})

    assert response.status_code == 409
    assert "stale_readiness_snapshot" in response.json()["detail"]


def test_no_request_body_variant_enables_override_new(
    client: TestClient, db_session, city_factory, place_factory,
) -> None:
    """Sweep a handful of plausible client payload shapes that a legacy or
    malicious client might send to try to smuggle the override through —
    none of them may succeed."""
    city = city_factory(slug="lockdown-sweep-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place-5", title="Lockdown Place 5")
    db_session.add(CityQualitySnapshot(city_id=city.id, readiness_score=40, quality_status="needs_review"))
    db_session.commit()

    payloads = [
        {"override_readiness_gate": True},
        {"override_readiness_gate": "true"},
        {"override_readiness_gate": 1},
        {"actor": "admin", "override_readiness_gate": True, "reason": "x"},
        {"force": True},
        {"bypass_gate": True},
    ]
    for payload in payloads:
        response = client.post(f"/admin/import-jobs/{city.id}/publish", json=payload)
        assert response.status_code == 409, f"payload {payload} unexpectedly bypassed the gate"


def test_internal_service_override_remains_explicit_and_audited_new(
    db_session, city_factory, place_factory,
) -> None:
    """The service-only override still exists for direct Python callers
    (tests, internal emergency scripts) and remains explicit (a keyword
    argument, not a default-True path) and audited (readiness_gate_overridden
    recorded in the admin audit log's new_value)."""
    from models.admin_audit_log import AdminAuditLog

    city = city_factory(slug="lockdown-internal-override-city", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="lockdown-place-6", title="Lockdown Place 6")
    db_session.commit()

    result = publish_city(db_session, city.id, actor="internal-emergency-script", override_readiness_gate=True)

    assert result is not None
    db_session.refresh(city)
    assert city.launch_status == "published"

    audit_row = (
        db_session.query(AdminAuditLog)
        .filter(AdminAuditLog.entity_type == "city", AdminAuditLog.action == "publish_city")
        .order_by(AdminAuditLog.id.desc())
        .first()
    )
    assert audit_row is not None
    assert audit_row.new_value["readiness_gate_overridden"] is True
