from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class BotSession(Base):
    """Persistent Telegram UI state.

    The bot keeps navigation state server-side so callback_data stays short and
    Telegram's 64-byte limit is never used as a state container.
    """

    __tablename__ = "bot_sessions"

    telegram_user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_city_slug: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    current_flow: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    last_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nav_stack: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list, nullable=False)
    short_ids: Mapped[dict[str, str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False)
    route_session: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    favorites: Mapped[dict[str, list[int]]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=lambda: {"places": [], "routes": []},
        nullable=False,
    )
    last_location: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
