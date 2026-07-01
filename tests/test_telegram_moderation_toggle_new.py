import asyncio
from types import SimpleNamespace

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardRemove

from models.feature_toggle import FeatureToggle
from telegram_bot.handlers.admin_moderation import cmd_moderation
from telegram_bot.handlers.catalog import _main_menu_markup, text_message
from telegram_bot.handlers.admin_moderation import router as admin_moderation_router
from telegram_bot.handlers.catalog import router as catalog_router
from telegram_bot.keyboards import catalog as catalog_keyboard
from telegram_bot.main import create_dispatcher


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
