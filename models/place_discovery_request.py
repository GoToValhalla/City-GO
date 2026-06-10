from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PlaceDiscoveryRequest(Base):
    __tablename__ = "place_discovery_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    scope_id: Mapped[int | None] = mapped_column(ForeignKey("city_import_scopes.id"), nullable=True)
    submitted_by_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_by_telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    submitted_by_anonymous_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_by_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="user_report")
    source_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    category_hint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    website: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="new", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    duplicate_place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
