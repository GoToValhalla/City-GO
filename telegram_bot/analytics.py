from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from models.bot_event import BotEvent
from models.bot_session import BotSession

logger = logging.getLogger("citygo.telegram.events")


def log_event(
    db: Session,
    session: BotSession,
    event_type: str,
    *,
    entity_type: str | None = None,
    entity_id: int | str | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    try:
        db.add(
            BotEvent(
                telegram_user_id=session.telegram_user_id,
                event_type=event_type,
                city_slug=session.selected_city_slug,
                entity_type=entity_type,
                entity_id=str(entity_id) if entity_id is not None else None,
                payload=payload,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write Telegram bot event")
