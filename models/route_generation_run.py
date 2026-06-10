"""Диагностика попытки генерации маршрута."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base


class RouteGenerationRun(Base):
    __tablename__ = "route_generation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    request_json: Mapped[dict[str, object] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    algorithm_version: Mapped[str] = mapped_column(String(64), nullable=False)
    total_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eligible_candidates: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    selected_places: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    candidates: Mapped[list["RouteGenerationCandidate"]] = relationship(
        "RouteGenerationCandidate", back_populates="run", cascade="all, delete-orphan",
    )
