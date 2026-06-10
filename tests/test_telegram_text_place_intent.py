from telegram_bot.services.text_intent import parse_text_place_intent


def test_parse_open_now_place_intent() -> None:
    intent = parse_text_place_intent("Что открыто в Зеленоградске?")
    assert intent is not None
    assert intent.kind == "open_now"
    assert intent.city_query == "зеленоградске"


def test_parse_coffee_place_intent() -> None:
    intent = parse_text_place_intent("Где кофе рядом с Курортным проспектом")
    assert intent is not None
    assert intent.kind == "coffee"


def test_parse_food_place_intent() -> None:
    intent = parse_text_place_intent("Хочу поесть в центре")
    assert intent is not None
    assert intent.kind == "food"


def test_parse_ignores_plain_text() -> None:
    assert parse_text_place_intent("привет, как дела") is None
