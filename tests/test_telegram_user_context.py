from telegram_bot.services.user_context import get_user_route, save_user_route


def test_save_and_get_user_route() -> None:
    route = {"route_id": "r1", "points": []}
    save_user_route(1001, route)
    assert get_user_route(1001) == route
