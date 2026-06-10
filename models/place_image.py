from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

PLACE_IMAGE_STATUS_NEEDS_REVIEW = "needs_review"
PLACE_IMAGE_STATUS_APPROVED = "approved"
PLACE_IMAGE_STATUS_REJECTED = "rejected"
PLACE_IMAGE_STATUS_ACTIVE = "active"
PLACE_IMAGE_STATUS_UNAVAILABLE = "unavailable"

PUBLIC_PLACE_IMAGE_STATUSES = frozenset(
    {PLACE_IMAGE_STATUS_APPROVED, PLACE_IMAGE_STATUS_ACTIVE}
)


class PlaceImage(Base):
    """Кандидат или подтверждённое изображение места (очередь ручной проверки)."""

    __tablename__ = "place_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    image_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    source_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    attribution: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    license: Mapped[str | None] = mapped_column(String(255), nullable=True)

    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PLACE_IMAGE_STATUS_NEEDS_REVIEW,
        index=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    place = relationship("Place", back_populates="images")
