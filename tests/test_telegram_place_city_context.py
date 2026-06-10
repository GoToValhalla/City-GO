import asyncio

from telegram_bot.services.address_context import save_user_address
from telegram_bot.services.place_city_context import resolve_place_city_slug
from telegram_bot.services.recommendation_client import RecommendationApiClient
from telegram_bot.services.user_context import reset_user_context, save_user_city


class _Client(RecommendationApiClient):
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    async def get_city_center_for_address(self, raw_address: str) -> dict[str, object]:
        return self.payload


class _QueryFallbackClient(RecommendationApiClient):
    async def get_city_center_for_address(self, raw_address: str) -> dict[str, object]:
        return (
            {"slug": "default", "matched": False}
            if raw_address == "где кофе"
            else {"slug": "zelenogradsk"}
        )


def test_place_city_slug_uses_saved_address_city() -> None:
    reset_user_context(4001)
    save_user_address(4001, "Зеленоградск, Курортный проспект")
    slug = asyncio.run(resolve_place_city_slug(4001, _Client({"slug": "zelenogradsk"})))
    assert slug == "zelenogradsk"


def test_place_city_slug_prefers_matched_query_city() -> None:
    reset_user_context(4004)
    save_user_address(4004, "Москва")
    slug = asyncio.run(
        resolve_place_city_slug(
            4004,
            _Client({"slug": "zelenogradsk", "matched": True}),
            "где кофе в Зеленоградске",
        )
    )
    assert slug == "zelenogradsk"


def test_place_city_slug_keeps_address_when_query_not_matched() -> None:
    reset_user_context(4005)
    save_user_address(4005, "Зеленоградск")
    slug = asyncio.run(
        resolve_place_city_slug(
            4005,
            _QueryFallbackClient(),
            "где кофе",
        )
    )
    assert slug == "zelenogradsk"


def test_place_city_slug_without_address_returns_none() -> None:
    reset_user_context(4002)
    slug = asyncio.run(resolve_place_city_slug(4002, _Client({"slug": "other"})))
    assert slug is None


def test_place_city_slug_without_backend_slug_returns_none() -> None:
    reset_user_context(4003)
    save_user_address(4003, "Неизвестный адрес")
    slug = asyncio.run(resolve_place_city_slug(4003, _Client({"ok": False})))
    assert slug is None


def test_place_city_slug_uses_selected_city_without_address() -> None:
    reset_user_context(4006)
    save_user_city(4006, "zelenogradsk")
    slug = asyncio.run(resolve_place_city_slug(4006, _Client({"ok": False})))
    assert slug == "zelenogradsk"
