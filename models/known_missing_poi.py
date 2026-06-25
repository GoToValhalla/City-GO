from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class KnownMissingPoi(Base):
    """Реестр must-have POI, которые City GO должен покрыть или объяснить.

    Это не источник импортируемых мест, а контрольный слой качества данных.
    Запись фиксирует ожидаемое место, его статус сверки и причину gap-а.
    """

    __tablename__ = "known_missing_poi"
    __table_args__ = (
        UniqueConstraint("city_id", "slug", name="uq_known_missing_poi_city_slug"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    matched_place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)

    # Stable code inside one city. It lets seeds, admin actions and reports reference the same POI.
    slug: Mapped[str] = mapped_column(String(160), nullable=False, index=True)

    name_local: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_ru: Mapped[str | None] = mapped_column(String(255), nullable=True)

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    coordinate_precision: Mapped[str] = mapped_column(String(32), nullable=False, default="approximate")

    expected_category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expected_scope: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expected_route_policy: Mapped[str] = mapped_column(String(64), nullable=False, default="must_have", index=True)
    significance: Mapped[str] = mapped_column(String(64), nullable=False, default="local", index=True)

    source: Mapped[str] = mapped_column(String(64), nullable=False, default="manual_seed", index=True)
    external_refs: Mapped[list[dict[str, str]] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    reporter_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="missing", index=True)
    gap_reason: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    city = relationship("City")
    matched_place = relationship("Place", foreign_keys=[matched_place_id])
