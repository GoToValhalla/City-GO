import asyncio
from types import SimpleNamespace

import pytest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardRemove

from models.feature_toggle import FeatureToggle
from telegram_bot.handlers.admin_moderation import cmd_moderation
from telegram_bot.handlers.catalog import _main_menu_markup, text_message
from telegram_bot.handlers.admin_moderation import router as admin_moderation_router
from telegram_bot.handlers.catalog import router as catalog_router
from telegram_bot.keyboards import catalog as catalog_keyboard
from telegram_bot.main import _validate_mini_app_config, create_dispatcher


OLD_REPLY_LABELS = {
    "Собрать маршрут",
    "Маршрут короче",
    "Убрать первую точку",
    "Что рядом",
    "Где кофе",
    "Где поесть",
    "Куда погулять",
    "С собакой",
    "Ввести адрес",
}


class _FakeMessage:
    text = "/moderation"
    chat = SimpleNamespace(id=123)
    from_user = SimpleNamespace(id=123)

    def __init__(self) -> None:
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, reply_markup=None):
        self.answers.append((text, reply_markup))


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, tb):
        return False


def _inline_texts(markup: InlineKeyboardMarkup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_main_menu_has_no_legacy_reply_labels_new() -> None:
    keyboard = catalog_keyboard.main_menu()

    assert isinstance(keyboard, InlineKeyboardMarkup)
    assert OLD_REPLY_LABELS.isdisjoint(set(_inline_texts(keyboard)))


def test_telegram_moderation_toggle_controls_main_menu_new(db_session) -> None:
    disabled = _main_menu_markup(db_session)
    assert "🛠 Модерация" not in _inline_texts(disabled)
    db_session.add(FeatureToggle(key="telegram_admin_moderation", scope="global", scope_id=None, value_bool=True))
    db_session.commit()

    enabled = _main_menu_markup(db_session)

    assert "🛠 Модерация" in _inline_texts(enabled)


def test_moderation_command_disabled_by_toggle_new(db_session, monkeypatch) -> None:
    message = _FakeMessage()
    monkeypatch.setattr("telegram_bot.handlers.admin_moderation.SessionLocal", lambda: _SessionContext(db_session))

    asyncio.run(cmd_moderation(message))

    assert any("Модерация временно выключена" in text for text, _markup in message.answers)
    assert isinstance(message.answers[-1][1], ReplyKeyboardRemove)


def test_slash_commands_do_not_hit_catalog_text_fallback_new() -> None:
    message = _FakeMessage()
    message.text = "/menu"

    asyncio.run(text_message(message))

    assert message.answers == []


def test_admin_moderation_router_is_before_catalog_catch_all_new() -> None:
    routers = create_dispatcher().sub_routers

    assert routers.index(admin_moderation_router) < routers.index(catalog_router)


def test_mini_app_button_hidden_when_tma_toggle_disabled_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    keyboard = catalog_keyboard.main_menu(tma_enabled=False)

    assert "🚀 Открыть City GO" not in _inline_texts(keyboard)


def test_mini_app_button_shown_when_tma_toggle_enabled_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    keyboard = catalog_keyboard.main_menu(tma_enabled=True)
    texts = _inline_texts(keyboard)
    urls = [button.web_app.url for row in keyboard.inline_keyboard for button in row if button.web_app]

    assert "🚀 Открыть City GO" in texts
    assert any(url.endswith("/telegram") for url in urls)


def test_tma_toggle_controls_main_menu_button_new(db_session, monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    # No explicit toggle row: tma_enabled defaults ON (project rule: all
    # non-AI feature flags default ON), so the button must be present.
    enabled_by_default = _main_menu_markup(db_session)
    assert "🚀 Открыть City GO" in _inline_texts(enabled_by_default)

    db_session.add(FeatureToggle(key="tma_enabled", scope="global", scope_id=None, value_bool=False))
    db_session.commit()

    disabled = _main_menu_markup(db_session)
    assert "🚀 Открыть City GO" not in _inline_texts(disabled)


def test_request_location_mini_app_button_gated_by_toggle_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    disabled = catalog_keyboard.request_location(tma_enabled=False)
    enabled = catalog_keyboard.request_location(tma_enabled=True)
    enabled_urls = [button.web_app.url for row in enabled.inline_keyboard for button in row if button.web_app]

    assert "🚀 Открыть City GO" not in _inline_texts(disabled)
    assert "🚀 Открыть City GO" in _inline_texts(enabled)
    assert any(url.endswith("/telegram/places") for url in enabled_urls)


def test_mini_app_url_missing_is_logged_new(monkeypatch, caplog) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "")

    with caplog.at_level("WARNING"):
        button = catalog_keyboard._mini_app_button("🚀 Открыть City GO", "/telegram")

    assert button is None
    assert any("TELEGRAM_MINI_APP_URL" in record.message for record in caplog.records)


def test_startup_fails_fast_when_mini_app_url_missing_in_production_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "telegram_mini_app_url", "")

    with pytest.raises(ValueError, match="TELEGRAM_MINI_APP_URL"):
        _validate_mini_app_config()


def test_startup_fails_fast_when_mini_app_url_invalid_in_production_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "telegram_mini_app_url", "http://not-https.example.com")

    with pytest.raises(ValueError, match="TELEGRAM_MINI_APP_URL"):
        _validate_mini_app_config()


def test_startup_passes_when_mini_app_url_valid_in_production_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    _validate_mini_app_config()


def test_startup_skips_mini_app_validation_outside_production_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "app_env", "local")
    monkeypatch.setattr(settings, "telegram_mini_app_url", "")

    _validate_mini_app_config()


def test_smoke_keyboard_contains_valid_webapp_button_new(monkeypatch) -> None:
    from core.config import settings

    monkeypatch.setattr(settings, "telegram_mini_app_url", "https://tma.example.com")

    keyboard = catalog_keyboard.main_menu(tma_enabled=True)
    webapp_buttons = [
        button for row in keyboard.inline_keyboard for button in row if button.web_app is not None
    ]

    assert webapp_buttons, "main menu keyboard must contain at least one WebApp button when TMA is enabled"
    assert webapp_buttons[0].web_app.url.startswith("https://tma.example.com")
