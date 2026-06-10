from telegram_bot.services.text_intent import parse_text_nearby_intent


def test_parse_nearby_text_intent() -> None:
    intent = parse_text_nearby_intent("Что рядом в Зеленоградске?")
    assert intent is not None
    assert intent.city_query == "Что рядом в Зеленоградске?"


def test_parse_nearby_synonym() -> None:
    intent = parse_text_nearby_intent("Покажи места поблизости")
    assert intent is not None


def test_nearby_intent_ignores_plain_text() -> None:
    assert parse_text_nearby_intent("где кофе") is None
