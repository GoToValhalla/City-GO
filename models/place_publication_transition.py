from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PlacePublicationTransition(Base):
    """Append-only history of authoritative place publication transitions."""

    __tablename__ = "place_publication_transitions"
    __table_args__ = (
        Index(
            "ix_place_publication_transitions_place_created",
            "place_id",
            "created_at",
        ),
        Index("ix_place_publication_transitions_reason_code", "reason_code"),
        Index("ix_place_publication_transitions_correlation_id", "correlation_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    place_id: Mapped[int] = mapped_column(
        ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    reason_details: Mapped[dict[str, object]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False
    )
    human_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    correlation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    place = relationship("Place", back_populates="publication_transitions")
