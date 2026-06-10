import json
import logging
from datetime import datetime

logger = logging.getLogger("citygo.telegram.events")


def log_telegram_event(
    user_id: int | None,
    action_type: str,
    *,
    city: str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    event = {
        "ts": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "action_type": action_type,
        "city": city,
        "payload": payload or {},
    }
    logger.info(json.dumps(event, ensure_ascii=False, sort_keys=True))
