import asyncio

from telegram_bot.services.city_fallback import UNSUPPORTED_CITY_TEXT, unsupported_city_message


class _Client:
    def __init__(self, matched: bool):
        self.matched = matched

    async def get_city_center_for_address(self, _raw_address: str) -> dict[str, object]:
        return {"matched": self.matched, "ok": self.matched, "slug": "zelenogradsk"}


def test_unsupported_city_message_returns_none_without_city_query() -> None:
    assert asyncio.run(unsupported_city_message(_Client(False), None)) is None


def test_unsupported_city_message_returns_none_when_city_matches() -> None:
    assert asyncio.run(unsupported_city_message(_Client(True), "Зеленоградск")) is None


def test_unsupported_city_message_returns_fallback_for_unknown_city() -> None:
    assert asyncio.run(unsupported_city_message(_Client(False), "Москва")) == UNSUPPORTED_CITY_TEXT
