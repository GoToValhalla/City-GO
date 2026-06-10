from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class TelegramUserContext(Base):
    __tablename__ = "telegram_user_contexts"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    last_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_city_slug: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_state: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
