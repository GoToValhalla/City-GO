from telegram_bot.keyboards.city_selection import city_selection_keyboard, city_slug_from_callback
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.city_selection import city_by_slug
from telegram_bot.services.user_context import get_user_city, reset_user_context, save_user_city


def test_city_callback_codes_are_short():
    assert city_slug_from_callback("city:zel") == "zelenogradsk"
    keyboard = city_selection_keyboard([{"slug": "khanty-mansiysk", "name": "Ханты-Мансийск"}])
    assert keyboard.inline_keyboard[0][0].callback_data == "city:khm"


def test_selected_city_is_saved_without_default():
    reset_user_context(901)
    assert get_user_city(901) is None
    save_user_city(901, "zelenogradsk")
    assert get_user_city(901) == "zelenogradsk"


def test_city_lookup_knows_draft_status():
    city = city_by_slug([{"slug": "kutaisi", "launch_status": "draft"}], "kutaisi")
    assert city and city["launch_status"] == "draft"


def test_main_menu_is_short_and_has_no_duplicate_actions():
    keyboard = get_main_menu_keyboard()
    labels = [button.text for row in keyboard.keyboard for button in row]
    assert len(labels) == 5
    assert len(set(labels)) == 5
