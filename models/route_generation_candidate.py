"""Per-place диагностика генерации маршрута."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base


class RouteGenerationCandidate(Base):
    __tablename__ = "route_generation_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    generation_run_id: Mapped[int] = mapped_column(
        ForeignKey("route_generation_runs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    is_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rejection_reasons: Mapped[list[str] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True,
    )
    selection_reasons: Mapped[list[str] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True,
    )

    run: Mapped["RouteGenerationRun"] = relationship("RouteGenerationRun", back_populates="candidates")
