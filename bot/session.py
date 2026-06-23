from __future__ import annotations

import secrets
import string

from sqlalchemy.orm import Session

from models.bot_session import BotSession

_SHORT_ID_ALPHABET = string.ascii_letters + string.digits


class BotSessionRepo:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create(self, telegram_user_id: int, username: str | None = None) -> BotSession:
        session = self.db.get(BotSession, telegram_user_id)
        if session is None:
            session = BotSession(
                telegram_user_id=telegram_user_id,
                username=username,
                nav_stack=[],
                short_ids={},
                favorites={"places": [], "routes": []},
            )
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        elif username and session.username != username:
            session.username = username
            self.db.commit()
            self.db.refresh(session)
        return session

    def save(self, session: BotSession) -> BotSession:
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session


def push_nav(session: BotSession, callback_data: str, max_depth: int = 10) -> None:
    stack = list(session.nav_stack or [])
    if not stack or stack[-1] != callback_data:
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


def _new_short_id(existing: dict[str, str]) -> str:
    while True:
        value = "".join(secrets.choice(_SHORT_ID_ALPHABET) for _ in range(4))
        if value not in existing:
            return value
