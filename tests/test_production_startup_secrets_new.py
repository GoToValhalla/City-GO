"""Regression coverage for main.py's production startup secret gate.

Root cause fixed: commit 6c887194b5685d3546d6148e5f4154414415158e added a
BOT_WEBHOOK_SECRET requirement keyed on BOT_TOKEN/TELEGRAM_BOT_TOKEN being
set, but the production bot runs in polling mode (telegram_bot_main.py ->
telegram_bot/main.py::run_polling()) and never uses BOT_WEBHOOK_SECRET --
only the webhook HTTP endpoint (routers/telegram_bot_webhook.py) does, and
that endpoint is not part of the active production bot flow. The startup
gate incorrectly treated "a bot token is configured" as evidence that
webhook mode is active, causing production to fail to start even though
the missing secret was not required for the transport actually in use.
"""

from __future__ import annotations

import asyncio

import pytest

import main as app_main


async def _run_lifespan_once(monkeypatch) -> None:
    """Drive main.py's lifespan() through one full enter/exit cycle with
    every scheduler start/stop replaced by a no-op, so only the
    production-secret validation logic under test has any real effect."""
    for name in (
        "start_place_verification_scheduler",
        "start_import_worker_scheduler",
        "start_route_state_cleanup_scheduler",
        "start_admin_background_operation_scheduler",
    ):
        monkeypatch.setattr(app_main, name, lambda: None)

    async def _noop_async() -> None:
        return None

    for name in (
        "stop_admin_background_operation_scheduler",
        "stop_route_state_cleanup_scheduler",
        "stop_import_worker_scheduler",
        "stop_place_verification_scheduler",
    ):
        monkeypatch.setattr(app_main, name, _noop_async)

    monkeypatch.setattr(app_main, "validate_route_state_runtime_config", lambda: None)

    async with app_main.lifespan(app_main.app):
        pass


def _set_production_env(monkeypatch, **overrides) -> None:
    monkeypatch.setattr(app_main.settings, "app_env", "production")
    monkeypatch.setattr(app_main.settings, "admin_api_token", overrides.get("admin_api_token", "admin-token"))
    monkeypatch.setattr(app_main.settings, "user_route_state_secret", overrides.get("user_route_state_secret", "route-secret"))
    monkeypatch.setattr(app_main.settings, "bot_token", overrides.get("bot_token", ""))
    monkeypatch.setattr(app_main.settings, "telegram_bot_token", overrides.get("telegram_bot_token", ""))
    monkeypatch.setattr(app_main.settings, "bot_webhook_secret", overrides.get("bot_webhook_secret", ""))


def test_production_startup_succeeds_with_bot_token_and_no_webhook_secret_new(monkeypatch) -> None:
    """The exact production shape that was broken: ADMIN_API_TOKEN and
    USER_ROUTE_STATE_SECRET set, BOT_TOKEN set (polling bot), no
    BOT_WEBHOOK_SECRET -- startup must succeed."""
    _set_production_env(monkeypatch, bot_token="123456:polling-bot-token", bot_webhook_secret="")
    asyncio.run(_run_lifespan_once(monkeypatch))


def test_production_startup_succeeds_with_telegram_bot_token_and_no_webhook_secret_new(monkeypatch) -> None:
    _set_production_env(monkeypatch, telegram_bot_token="123456:alerts-bot-token", bot_webhook_secret="")
    asyncio.run(_run_lifespan_once(monkeypatch))


def test_production_startup_succeeds_with_no_bot_token_at_all_new(monkeypatch) -> None:
    _set_production_env(monkeypatch)
    asyncio.run(_run_lifespan_once(monkeypatch))


def test_production_startup_fails_when_admin_api_token_missing_new(monkeypatch) -> None:
    _set_production_env(monkeypatch, admin_api_token="", bot_token="123456:polling-bot-token")
    with pytest.raises(RuntimeError, match="ADMIN_API_TOKEN"):
        asyncio.run(_run_lifespan_once(monkeypatch))


def test_production_startup_fails_when_user_route_state_secret_missing_new(monkeypatch) -> None:
    _set_production_env(monkeypatch, user_route_state_secret="", bot_token="123456:polling-bot-token")
    with pytest.raises(RuntimeError, match="USER_ROUTE_STATE_SECRET"):
        asyncio.run(_run_lifespan_once(monkeypatch))


def test_production_startup_never_mentions_bot_webhook_secret_new(monkeypatch) -> None:
    """Direct regression guard: BOT_WEBHOOK_SECRET must never appear in the
    startup failure message, regardless of bot token / webhook secret
    configuration -- the gate no longer considers it at all."""
    _set_production_env(monkeypatch, admin_api_token="", bot_token="123456:polling-bot-token", bot_webhook_secret="")
    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(_run_lifespan_once(monkeypatch))
    assert "BOT_WEBHOOK_SECRET" not in str(excinfo.value)


def test_non_production_startup_ignores_all_secret_requirements_new(monkeypatch) -> None:
    monkeypatch.setattr(app_main.settings, "app_env", "local")
    monkeypatch.setattr(app_main.settings, "admin_api_token", "")
    monkeypatch.setattr(app_main.settings, "user_route_state_secret", "")
    monkeypatch.setattr(app_main.settings, "bot_token", "")
    monkeypatch.setattr(app_main.settings, "telegram_bot_token", "")
    monkeypatch.setattr(app_main.settings, "bot_webhook_secret", "")
    asyncio.run(_run_lifespan_once(monkeypatch))
