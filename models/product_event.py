"""Простые product events для метрик."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ProductEvent(Base):
    __tablename__ = "product_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    city_slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
