from datetime import datetime, timedelta, timezone

from models.bot_session import BotSession
from telegram_bot.services.pending_location import (
    clear_temporary_location,
    consume_pending_intent,
    get_temporary_location,
    save_temporary_location,
    set_pending_intent,
)


def test_pending_nearby_and_route_intents_new():
    session = BotSession(telegram_user_id=1)
    set_pending_intent(session, "nearby")
    assert consume_pending_intent(session) == "nearby"
    set_pending_intent(session, "continue_route")
    assert consume_pending_intent(session) == "continue_route"


def test_pending_intent_ttl_new():
    session = BotSession(telegram_user_id=2)
    session.current_flow = "await_location:build_route:1"
    assert consume_pending_intent(session) is None


def test_temporary_location_ttl_and_clear_new():
    session = BotSession(telegram_user_id=3)
    save_temporary_location(session, 54.9, 20.4)
    assert get_temporary_location(session)["lat"] == 54.9
    session.last_location["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    assert get_temporary_location(session) is None
    save_temporary_location(session, 54.9, 20.4)
    clear_temporary_location(session)
    assert session.last_location is None
