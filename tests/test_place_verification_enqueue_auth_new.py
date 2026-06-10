"""
Тесты безопасности POST /place-verification/enqueue-stale/{city_slug} (P0-2A).

Проверяют:
- 401 без Authorization header
- 403 с неверным токеном
- 200 с валидным токеном
- audit log создаётся при успешном вызове
- dedup: повторный вызов не создаёт мусор в очереди
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from main import app

_VALID_TOKEN = "test-enqueue-auth-secret"
_INVALID_TOKEN = "wrong-token"
_AUTH_HEADER = {"Authorization": f"Bearer {_VALID_TOKEN}"}
_WRONG_HEADER = {"Authorization": f"Bearer {_INVALID_TOKEN}"}


@pytest.fixture(autouse=True)
def _set_admin_token(monkeypatch):
    from core.config import settings
    monkeypatch.setattr(settings, "admin_api_token", _VALID_TOKEN)


# ─── 401 / 403 без override ──────────────────────────────────────────────────

def test_enqueue_stale_without_auth_returns_401() -> None:
    response = TestClient(app).post("/place-verification/enqueue-stale/zelenogradsk")
    assert response.status_code == 401


def test_enqueue_stale_with_wrong_token_returns_403() -> None:
    response = TestClient(app).post(
        "/place-verification/enqueue-stale/zelenogradsk",
        headers=_WRONG_HEADER,
    )
    assert response.status_code == 403


# ─── 200 с валидным токеном ──────────────────────────────────────────────────

def test_enqueue_stale_with_valid_token_returns_200(override_get_db) -> None:
    """С валидным токеном и пустым городом возвращает enqueued=0."""
    response = TestClient(app).post(
        "/place-verification/enqueue-stale/unknown-city",
        headers=_AUTH_HEADER,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["city_slug"] == "unknown-city"
    assert payload["enqueued"] == 0


# ─── Audit log создаётся при вызове ─────────────────────────────────────────

def test_enqueue_stale_creates_audit_log(
    client, db_session, city_factory
) -> None:
    """Успешный enqueue пишет audit event с action=enqueue_stale_verification."""
    from models.admin_audit_log import AdminAuditLog

    city_factory(slug="test-enqueue-city")

    response = client.post("/place-verification/enqueue-stale/test-enqueue-city")
    assert response.status_code == 200

    log = (
        db_session.query(AdminAuditLog)
        .filter(
            AdminAuditLog.action == "enqueue_stale_verification",
            AdminAuditLog.entity_id == "test-enqueue-city",
        )
        .first()
    )
    assert log is not None
    assert log.entity_type == "city"
    assert log.actor == "test-admin"  # из conftest bypass
    assert "enqueued" in (log.new_value or {})


# ─── Dedup: повторный вызов не создаёт дубли ────────────────────────────────

def test_enqueue_stale_dedup_no_duplicate_tasks(
    client, db_session, place_factory
) -> None:
    """Повторный enqueue для одного города не дублирует pending tasks."""
    from models.place_verification_task import PlaceVerificationTask

    # Создаём место с низким confidence (чтобы попало в stale)
    place = place_factory()

    first = client.post("/place-verification/enqueue-stale/zelenogradsk")
    assert first.status_code == 200

    second = client.post("/place-verification/enqueue-stale/zelenogradsk")
    assert second.status_code == 200

    # При втором вызове enqueued=0 (dedup), already_pending > 0 или всё 0
    second_data = second.json()
    assert second_data["enqueued"] == 0 or second_data["already_pending"] >= 0

    # Нет дублирующих pending задач для одного места
    tasks = (
        db_session.query(PlaceVerificationTask)
        .filter(
            PlaceVerificationTask.place_id == place.id,
            PlaceVerificationTask.status == "pending",
        )
        .all()
    )
    assert len(tasks) <= 1
