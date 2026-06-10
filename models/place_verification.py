from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PlaceVerification(Base):
    """Audit-log ручных и системных подтверждений существования места."""

    __tablename__ = "place_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    confidence_score_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_level_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confidence_level_after: Mapped[str | None] = mapped_column(String(32), nullable=True)

    verification_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verification_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verifier: Mapped[str | None] = mapped_column(String(255), nullable=True)

    verifier_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    verifier_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_to_place_meters: Mapped[float | None] = mapped_column(Float, nullable=True)

    photo_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
