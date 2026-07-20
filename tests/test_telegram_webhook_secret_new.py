"""Telegram webhook secret: fail-closed + constant-time compare."""

from __future__ import annotations

from fastapi.testclient import TestClient

from core.config import settings
from main import app


def test_telegram_webhook_rejects_missing_secret_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "bot_webhook_secret", "")
    monkeypatch.setattr(settings, "app_env", "production")
    response = TestClient(app).post("/telegram-bot/webhook", json={"update_id": 1})
    assert response.status_code == 503


def test_telegram_webhook_rejects_wrong_secret_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "bot_webhook_secret", "expected-secret-value")
    monkeypatch.setattr(settings, "bot_token", "bot-token")
    response = TestClient(app).post(
        "/telegram-bot/webhook",
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret-value"},
    )
    assert response.status_code == 403
