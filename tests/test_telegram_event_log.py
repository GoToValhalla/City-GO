import json
import logging

from telegram_bot.services.event_log import log_telegram_event


def test_log_telegram_event_writes_structured_json(caplog) -> None:
    caplog.set_level(logging.INFO, logger="citygo.telegram.events")
    log_telegram_event(42, "route_build_started", city="zelenogradsk", payload={"minutes": 120})
    data = json.loads(caplog.records[0].message)
    assert data["user_id"] == 42
    assert data["action_type"] == "route_build_started"
    assert data["city"] == "zelenogradsk"
    assert data["payload"] == {"minutes": 120}
