from telegram_bot.callbacks import cb
from telegram_bot.keyboards.catalog import CITY_LIST_VISIBLE_LIMIT, city_list
from telegram_bot.renderers import city_select_text
from telegram_bot.schemas import BotCity


def _cities(count: int) -> list[BotCity]:
    return [BotCity(id=index, slug=f"city-{index}", name=f"Город {index}", places_count=index * 10) for index in range(count)]


def test_city_picker_limits_visible_inline_buttons_new() -> None:
    keyboard = city_list(_cities(8))
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]
    city_callbacks = [item for item in callbacks if item and item.startswith("c:set:")]

    assert len(city_callbacks) == CITY_LIST_VISIBLE_LIMIT
    assert len(city_callbacks) == 5
    assert cb("m", "main") in callbacks
    assert all(len(item.encode("utf-8")) <= 64 for item in callbacks if item)


def test_city_picker_text_explains_supported_count_and_text_search_new() -> None:
    text = city_select_text(_cities(8))

    assert "Поддерживается городов: <b>8</b>" in text
    assert "На кнопках показаны 5" in text
    assert "Еще 3" in text
    assert "написать название сообщением" in text
    assert "Астрахань" in text


def test_city_picker_text_handles_short_city_list_new() -> None:
    text = city_select_text(_cities(3))

    assert "Поддерживается городов: <b>3</b>" in text
    assert "Все доступные города показаны" in text
    assert "Еще" not in text
