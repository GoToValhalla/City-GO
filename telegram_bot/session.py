from __future__ import annotations

import secrets
import string
from datetime import datetime

from sqlalchemy.orm import Session

from models.bot_session import BotSession

_SHORT_ID_ALPHABET = string.ascii_letters + string.digits


def get_or_create_session(db: Session, telegram_user_id: int, username: str | None = None) -> BotSession:
    session = db.get(BotSession, telegram_user_id)
    if session is None:
        session = BotSession(
            telegram_user_id=telegram_user_id,
            username=username,
            nav_stack=[],
            short_ids={},
            favorites={"places": [], "routes": []},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    if username and session.username != username:
        session.username = username
        db.commit()
        db.refresh(session)
    return session


def save_session(db: Session, session: BotSession) -> BotSession:
    session.updated_at = datetime.utcnow()
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def push_nav(session: BotSession, callback_data: str, max_depth: int = 10) -> None:
    stack = list(session.nav_stack or [])
    if callback_data != "back" and (not stack or stack[-1] != callback_data):
        stack.append(callback_data)
    session.nav_stack = stack[-max_depth:]


def pop_nav(session: BotSession) -> str | None:
    stack = list(session.nav_stack or [])
    if len(stack) <= 1:
        session.nav_stack = []
        return None
    stack.pop()
    previous = stack[-1]
    session.nav_stack = stack
    return previous


def get_short_id(session: BotSession, full_id: int | str) -> str:
    full_value = str(full_id)
    short_ids = dict(session.short_ids or {})
    for short, stored in short_ids.items():
        if stored == full_value:
            return short
    short = _new_short_id(short_ids)
    short_ids[short] = full_value
    session.short_ids = short_ids
    return short


def resolve_short_id(session: BotSession, short_id: str) -> int | None:
    value = (session.short_ids or {}).get(short_id)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def toggle_favorite(session: BotSession, kind: str, entity_id: int) -> bool:
    key = "routes" if kind == "r" else "places"
    favorites = {"places": [], "routes": [], **(session.favorites or {})}
    values = list(favorites.get(key, []))
    if entity_id in values:
        values.remove(entity_id)
        added = False
    else:
        values.append(entity_id)
        added = True
    favorites[key] = values
    session.favorites = favorites
    return added


def _new_short_id(existing: dict[str, str]) -> str:
    while True:
        value = "".join(secrets.choice(_SHORT_ID_ALPHABET) for _ in range(4))
        if value not in existing:
            return value
