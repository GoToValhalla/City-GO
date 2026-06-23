"""Field-level confidence snapshots for imported/enriched places."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class PlaceFieldConfidence(Base):
    __tablename__ = "place_field_confidence"
    __table_args__ = (UniqueConstraint("place_id", "field_name", name="uq_place_field_confidence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    confidence_level: Mapped[str] = mapped_column(String(32), nullable=False, default="low", index=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="system", index=True)
    freshness_status: Mapped[str] = mapped_column(String(32), nullable=False, default="fresh", index=True)
    conflict_status: Mapped[str] = mapped_column(String(32), nullable=False, default="none", index=True)
    is_manual_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    raw_value: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
