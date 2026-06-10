from telegram_bot.services.text_intent import parse_text_route_intent


def test_parse_route_with_time_and_interests() -> None:
    intent = parse_text_route_intent("Собери маршрут на полтора часа: кофе и прогулка")
    assert intent is not None
    assert intent.minutes == 90
    assert intent.interests == ("cafe", "walk")
    assert intent.city_query == "Собери маршрут на полтора часа: кофе и прогулка"


def test_parse_avoided_category() -> None:
    intent = parse_text_route_intent("Маршрут на 2 часа без музеев, хочу поесть")
    assert intent is not None
    assert intent.minutes == 120
    assert intent.interests == ("food",)
    assert intent.avoided_categories == ("museum",)


def test_ignores_plain_non_route_text() -> None:
    assert parse_text_route_intent("привет, как дела") is None


def test_parse_route_keeps_city_query_text() -> None:
    intent = parse_text_route_intent("Маршрут в Калининграде на час")
    assert intent is not None
    assert intent.minutes == 60
    assert intent.city_query == "Маршрут в Калининграде на час"
