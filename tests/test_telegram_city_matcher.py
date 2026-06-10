from telegram_bot.services.city_matcher import match_city


def test_match_city_by_russian_name() -> None:
    city = match_city(
        [
            {"slug": "zelenogradsk", "name": "Зеленоградск", "is_active": True},
            {"slug": "kaliningrad", "name": "Калининград", "is_active": True},
        ],
        "Калининград, Ленинский проспект",
    )

    assert city is not None
    assert city["slug"] == "kaliningrad"


def test_match_city_ignores_inactive_city() -> None:
    city = match_city(
        [{"slug": "ghost", "name": "Город", "is_active": False}],
        "Город, улица",
    )

    assert city is None
