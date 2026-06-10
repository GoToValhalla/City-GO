import asyncio

from telegram_bot.services.address_context import save_user_address
from telegram_bot.services.nearby_start import resolve_nearby_start
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.user_context import reset_user_context, save_user_location


class _Client(RecommendationApiClient):
    async def get_city_center_for_address(self, raw_address: str) -> dict[str, object]:
        return {
            "ok": True,
            "lat": 54.959,
            "lng": 20.476,
            "name": "Зеленоградск",
            "matched": "Зеленоградск" in raw_address,
        }


def test_resolve_nearby_start_uses_saved_location_first() -> None:
    reset_user_context(3001)
    save_user_location(3001, 1.0, 2.0)
    start = asyncio.run(resolve_nearby_start(3001, _Client()))
    assert start is not None
    assert start.lat == 1.0
    assert start.source == "user_location"


def test_resolve_nearby_start_uses_manual_address() -> None:
    reset_user_context(3002)
    save_user_address(3002, "Зеленоградск, Курортный проспект")
    start = asyncio.run(resolve_nearby_start(3002, _Client()))
    assert start is not None
    assert start.lat == 54.959
    assert start.source == "manual_address"


def test_resolve_nearby_start_without_context_returns_none() -> None:
    reset_user_context(3003)
    assert asyncio.run(resolve_nearby_start(3003, _Client())) is None


def test_resolve_nearby_start_uses_city_from_text() -> None:
    reset_user_context(3004)
    start = asyncio.run(resolve_nearby_start(3004, _Client(), "Что рядом в Зеленоградске?"))
    assert start is not None
    assert start.lat == 54.959
    assert start.source == "text_city"
