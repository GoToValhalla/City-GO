from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class RouteBuildEvent(Base):
    __tablename__ = "route_build_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    route_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    user_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    city_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    total_places: Mapped[int] = mapped_column(Integer, nullable=False)
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    has_warnings: Mapped[bool] = mapped_column(Boolean, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    warnings: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    quality_breakdown: Mapped[dict[str, float]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
