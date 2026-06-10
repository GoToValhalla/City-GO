"""Агрегатор хендлеров кнопок поиска мест."""

from functools import reduce

from aiogram import Router

from telegram_bot.handlers.place_menu.city_categories import router as city_router
from telegram_bot.handlers.place_menu.extra_categories import router as extra_router
from telegram_bot.handlers.place_menu.nearby import router as nearby_router

CHILD_ROUTERS = (nearby_router, city_router, extra_router)


def _include(parent: Router, child: Router) -> Router:
    parent.include_router(child)
    return parent


router = reduce(_include, CHILD_ROUTERS, Router())
