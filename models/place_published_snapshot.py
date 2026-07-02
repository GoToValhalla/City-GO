from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PublishedPlaceSnapshot(Base):
    """Stage 1 public read projection for catalog/search/routing consumers."""

    __tablename__ = "published_place_snapshots"
    __table_args__ = (
        UniqueConstraint("place_id", "snapshot_version", name="uq_published_place_snapshot_place_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    snapshot_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), default="default", nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_status: Mapped[str] = mapped_column(String(32), default="not_public", nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_catalog_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_search_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_route_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    snapshot_payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    quality_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    media_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    source_event_type: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    source_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
