import asyncio

from telegram_bot.services.route_start import resolve_route_start
from telegram_bot.services.address_context import save_user_address
from telegram_bot.services.user_context import reset_user_context, save_user_city, save_user_location


class _Client:
    async def get_default_city_center(self):
        return {"ok": True, "lat": 54.96, "lng": 20.48}

    async def get_city_center_by_slug(self, slug):
        return {"ok": True, "lat": 54.96, "lng": 20.48, "slug": slug}

    async def get_city_center_for_address(self, raw_address):
        if "Калининград" in raw_address:
            return {
                "ok": True,
                "lat": 54.71,
                "lng": 20.51,
                "name": "Калининград",
                "matched": True,
            }
        return {"ok": True, "lat": 54.96, "lng": 20.48, "matched": False}


def test_resolve_route_start_uses_saved_location_first() -> None:
    reset_user_context(2001)
    save_user_location(2001, 1.0, 2.0)
    start = asyncio.run(resolve_route_start(2001, _Client()))
    assert start is not None
    assert start.lat == 1.0
    assert start.source == "user_location"


def test_resolve_route_start_uses_text_city_before_saved_location() -> None:
    reset_user_context(2005)
    save_user_location(2005, 1.0, 2.0)
    start = asyncio.run(
        resolve_route_start(2005, _Client(), city_query="маршрут в Калининград")
    )
    assert start is not None
    assert start.lat == 54.71
    assert start.source == "text_city"


def test_resolve_route_start_without_selected_city_returns_none() -> None:
    reset_user_context(2002)
    start = asyncio.run(resolve_route_start(2002, _Client()))
    assert start is None


def test_resolve_route_start_uses_selected_city_center() -> None:
    reset_user_context(2006)
    save_user_city(2006, "zelenogradsk")
    start = asyncio.run(resolve_route_start(2006, _Client()))
    assert start is not None
    assert start.source == "selected_city"


def test_resolve_route_start_uses_manual_address_before_default_city() -> None:
    reset_user_context(2003)
    save_user_address(2003, "Зеленоградск, Курортный проспект")
    start = asyncio.run(resolve_route_start(2003, _Client()))
    assert start is not None
    assert start.lat == 54.96
    assert start.source == "manual_address"
    assert "Курортный" in start.label


def test_resolve_route_start_uses_city_from_manual_address() -> None:
    reset_user_context(2004)
    save_user_address(2004, "Калининград, Ленинский проспект")
    start = asyncio.run(resolve_route_start(2004, _Client()))
    assert start is not None
    assert start.lat == 54.71
    assert start.source == "manual_address"
    assert "Калининград" in start.label
