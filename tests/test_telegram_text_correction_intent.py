from telegram_bot.services.text_intent import parse_text_correction_intent


def test_parse_shorten_correction() -> None:
    intent = parse_text_correction_intent("Сделай маршрут короче")
    assert intent is not None
    assert intent.action == "shorten_route"


def test_parse_avoid_category_correction() -> None:
    intent = parse_text_correction_intent("Без музеев, пожалуйста")
    assert intent is not None
    assert intent.action == "avoid_category"
    assert intent.avoided_categories == ("museum",)


def test_parse_rebuild_from_here_correction() -> None:
    intent = parse_text_correction_intent("Перестрой отсюда")
    assert intent is not None
    assert intent.action == "rebuild_from_here"


def test_parse_extend_route_correction() -> None:
    intent = parse_text_correction_intent("Добавь еще место")
    assert intent is not None
    assert intent.action == "extend_route"


def test_ignores_plain_text() -> None:
    assert parse_text_correction_intent("хочу кофе на час") is None
