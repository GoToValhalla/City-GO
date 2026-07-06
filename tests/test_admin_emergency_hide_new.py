from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from models.admin_audit_log import AdminAuditLog

_AUTH = {"Authorization": "Bearer test"}


def test_emergency_hide_requires_reason_new(client: TestClient, published_place_factory) -> None:
    place = published_place_factory(category="museum")
    response = client.post(
        f"/admin/places/{place.id}/emergency-hide",
        headers=_AUTH,
        json={"reason": "short", "idempotency_key": "hide-key-1"},
    )
    assert response.status_code == 422


def test_emergency_hide_hides_place_and_writes_audit_new(client: TestClient, db_session, published_place_factory) -> None:
    place = published_place_factory(category="museum")
    response = client.post(
        f"/admin/places/{place.id}/emergency-hide",
        headers=_AUTH,
        json={"reason": "Жалоба пользователя на закрытую локацию", "idempotency_key": "hide-key-2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["publication_status"] == "hidden"
    assert body["is_published"] is False
    assert body["is_visible_in_catalog"] is False
    assert body["is_route_eligible"] is False
    assert body["audit_log_id"] > 0

    db_session.refresh(place)
    assert place.publication_status == "hidden"
    assert place.is_visible_in_catalog is False
    audit = db_session.query(AdminAuditLog).filter(AdminAuditLog.id == body["audit_log_id"]).one()
    assert audit.action == "emergency_hide_place"
    assert audit.entity_id == str(place.id)


def test_emergency_hide_is_idempotent_new(client: TestClient, published_place_factory) -> None:
    place = published_place_factory(category="museum")
    payload = {"reason": "Срочное скрытие из-за подтвержденной ошибки данных", "idempotency_key": "hide-key-3"}
    first = client.post(f"/admin/places/{place.id}/emergency-hide", headers=_AUTH, json=payload)
    second = client.post(f"/admin/places/{place.id}/emergency-hide", headers=_AUTH, json=payload)
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["audit_log_id"] == first.json()["audit_log_id"]
    assert second.json()["idempotent_replay"] is True


def test_emergency_hide_removes_place_from_public_catalog_new(client: TestClient, city_factory, published_place_factory) -> None:
    city = city_factory(slug="emergency-public-city")
    place = published_place_factory(city_id=city.id, category="museum", title="Скрываемое место")

    response = client.post(
        f"/admin/places/{place.id}/emergency-hide",
        headers=_AUTH,
        json={"reason": "Подтвержденная жалоба на недоступное место", "idempotency_key": "hide-key-4"},
    )
    assert response.status_code == 200

    catalog = client.get(f"/places/?city_slug={city.slug}")
    assert catalog.status_code == 200
    ids = {item["id"] for item in catalog.json()["items"]}
    assert place.id not in ids

    detail = client.get(f"/places/{place.id}")
    assert detail.status_code == 404
