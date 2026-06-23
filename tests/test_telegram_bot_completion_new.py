from datetime import datetime

from models.bot_event import BotEvent
from services.admin_bot_analytics_service import get_bot_analytics_summary
from telegram_bot.keyboards.catalog import place_card, route_card, route_step
from telegram_bot.schemas import BotPlace, BotRoute, BotRoutePoint
from telegram_bot.session import get_or_create_session


def _buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_route_card_has_start_map_action_and_short_callbacks_new(db_session) -> None:
    session = get_or_create_session(db_session, 776655, "qa")
    route = BotRoute(
        id=5,
        title="Городская прогулка",
        points=[
            BotRoutePoint(index=0, place_id=10, title="Археопарк", lat=61.0042, lng=69.0019),
            BotRoutePoint(index=1, place_id=11, title="Парк", lat=61.0050, lng=69.0024),
        ],
    )

    markup = route_card(route, session)
    buttons = _buttons(markup)

    assert any(button.text == "🗺 Открыть карту" and button.url and "yandex" in button.url for button in buttons)
    assert all(
        len(button.callback_data.encode("utf-8")) <= 64
        for button in buttons
        if button.callback_data
    )


def test_route_step_has_external_map_and_short_callbacks_new() -> None:
    point = BotRoutePoint(
        index=0,
        place_id=10,
        title="Археопарк",
        lat=61.0042,
        lng=69.0019,
    )

    markup = route_step(point, total=3, is_visited=False)
    buttons = _buttons(markup)

    assert any(button.text == "🗺 На карте" and button.url and "yandex" in button.url for button in buttons)
    assert all(
        len(button.callback_data.encode("utf-8")) <= 64
        for button in buttons
        if button.callback_data
    )


def test_place_card_has_map_favorite_similar_and_short_callbacks_new(db_session) -> None:
    session = get_or_create_session(db_session, 998877, "qa")
    place = BotPlace(
        id=42,
        title="Coffee Like",
        category="food",
        lat=61.0042,
        lng=69.0019,
    )

    markup = place_card(place, session)
    buttons = _buttons(markup)

    assert any(button.text == "🗺 На карте" and button.url and "yandex" in button.url for button in buttons)
    assert any(button.text == "❤️ Сохранить" for button in buttons)
    assert any(button.text == "🔍 Похожие" and button.callback_data == "p:cat:food:0" for button in buttons)
    assert all(
        len(button.callback_data.encode("utf-8")) <= 64
        for button in buttons
        if button.callback_data
    )


def test_bot_admin_analytics_returns_route_funnel_and_no_result_searches_new(db_session) -> None:
    db_session.add_all(
        [
            BotEvent(
                telegram_user_id=1,
                event_type="route_started",
                city_slug="zelenogradsk",
                entity_type="route",
                entity_id="7",
                created_at=datetime.utcnow(),
            ),
            BotEvent(
                telegram_user_id=1,
                event_type="route_completed",
                city_slug="zelenogradsk",
                entity_type="route",
                entity_id="7",
                created_at=datetime.utcnow(),
            ),
            BotEvent(
                telegram_user_id=2,
                event_type="search_no_results",
                city_slug="zelenogradsk",
                payload={"query": "аквапарк"},
                created_at=datetime.utcnow(),
            ),
        ]
    )
    db_session.commit()

    summary = get_bot_analytics_summary(db_session, days=7)

    assert summary["active_users"] == 2
    assert summary["route_funnel"] == {
        "started": 1,
        "completed": 1,
        "completion_rate_percent": 100.0,
    }
    assert {item["key"]: item["count"] for item in summary["events_by_type"]}["search_no_results"] == 1
    assert summary["search_no_results"][0]["query"] == "аквапарк"
