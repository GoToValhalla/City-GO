"""Publication policy decisions for public catalog automation."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class PlacePublicationDecision(Base):
    __tablename__ = "place_publication_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow", index=True)
    decision: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="recorded", index=True)
    trust_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, index=True)
    failed_gates: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    review_reasons: Mapped[list[str] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
