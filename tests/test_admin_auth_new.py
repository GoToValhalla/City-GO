"""
Тесты безопасности admin/write endpoints (P0-2, P0-3, P0-6).

Проверяют:
- 401 при отсутствии Authorization header
- 403 при неверном токене
- 200 при верном токене
- client-provided actor игнорируется (P0-3)
- audit log создаётся для write-действий (P0-6)
- place image review approve/reject требует auth
- place verification admin endpoints требуют auth
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

_VALID_TOKEN = "test-admin-secret-for-auth-tests"
_INVALID_TOKEN = "wrong-token"
_AUTH_HEADER = {"Authorization": f"Bearer {_VALID_TOKEN}"}
_WRONG_HEADER = {"Authorization": f"Bearer {_INVALID_TOKEN}"}


@pytest.fixture(autouse=True)
def _set_admin_token(monkeypatch):
    """Устанавливает тестовый admin token через monkeypatch settings."""
    from core.config import settings
    monkeypatch.setattr(settings, "admin_api_token", _VALID_TOKEN)


# ─── Базовые 401/403 ──────────────────────────────────────────────────────────

def test_admin_dashboard_without_auth_returns_401() -> None:
    response = TestClient(app).get("/admin/dashboard")
    assert response.status_code == 401


def test_admin_dashboard_with_wrong_token_returns_403() -> None:
    response = TestClient(app).get("/admin/dashboard", headers=_WRONG_HEADER)
    assert response.status_code == 403


def test_admin_dashboard_with_valid_token_returns_200(override_get_db) -> None:
    response = TestClient(app).get("/admin/dashboard", headers=_AUTH_HEADER)
    assert response.status_code == 200


# ─── Actor не берётся из query/body (P0-3) ───────────────────────────────────

def test_client_provided_actor_in_body_is_ignored_on_publish(
    client, place_factory, db_session
) -> None:
    """payload.actor='evil-client' не должен попадать в audit log."""
    from models.admin_audit_log import AdminAuditLog

    place = place_factory()
    response = client.post(
        f"/admin/places/{place.id}/publish",
        json={"actor": "evil-client", "reason": "Test"},
    )
    assert response.status_code == 200

    log = db_session.query(AdminAuditLog).filter(
        AdminAuditLog.action == "publish_place",
        AdminAuditLog.entity_id == str(place.id),
    ).first()
    assert log is not None
    # В тестах auth bypassed → actor_id = "test-admin" из conftest override
    assert log.actor == "test-admin"
    assert log.actor != "evil-client"


# ─── Audit log создаётся для write-действий (P0-6) ───────────────────────────

def test_audit_log_created_on_place_publish(client, place_factory, db_session) -> None:
    from models.admin_audit_log import AdminAuditLog

    place = place_factory()
    response = client.post(
        f"/admin/places/{place.id}/publish",
        json={"reason": "Проверено"},
    )
    assert response.status_code == 200

    log = db_session.query(AdminAuditLog).filter(
        AdminAuditLog.action == "publish_place",
        AdminAuditLog.entity_id == str(place.id),
    ).first()
    assert log is not None
    assert log.entity_type == "place"


def test_audit_log_created_on_image_approve(client, db_session, place_factory) -> None:
    from datetime import datetime

    from models.admin_audit_log import AdminAuditLog
    from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage

    place = place_factory()
    image = PlaceImage(
        place_id=place.id,
        image_url="https://example.com/audit-test.jpg",
        source_type="osm_image",
        status=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(image)
    db_session.commit()

    response = client.post(f"/admin/place-images/{image.id}/approve")
    assert response.status_code == 200

    log = db_session.query(AdminAuditLog).filter(
        AdminAuditLog.action == "approve_place_image",
        AdminAuditLog.entity_id == str(image.id),
    ).first()
    assert log is not None
    assert log.actor == "test-admin"


# ─── Place image review требует auth ─────────────────────────────────────────

def test_place_image_approve_without_auth_returns_401() -> None:
    response = TestClient(app).post("/admin/place-images/1/approve")
    assert response.status_code == 401


def test_place_image_reject_without_auth_returns_401() -> None:
    response = TestClient(app).post("/admin/place-images/1/reject")
    assert response.status_code == 401


def test_place_image_approve_with_wrong_token_returns_403() -> None:
    response = TestClient(app).post(
        "/admin/place-images/1/approve", headers=_WRONG_HEADER
    )
    assert response.status_code == 403


# ─── Place verification admin endpoints требуют auth ─────────────────────────

def test_admin_place_verification_queue_without_auth_returns_401() -> None:
    response = TestClient(app).get("/admin/place-verifications/queue")
    assert response.status_code == 401


def test_admin_place_verify_without_auth_returns_401() -> None:
    response = TestClient(app).post(
        "/admin/place-verifications/places/1/verify",
        json={"action": "confirm"},
    )
    assert response.status_code == 401


def test_admin_place_verify_with_wrong_token_returns_403() -> None:
    response = TestClient(app).post(
        "/admin/place-verifications/places/1/verify",
        json={"action": "confirm"},
        headers=_WRONG_HEADER,
    )
    assert response.status_code == 403
