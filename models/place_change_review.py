"""LEGACY MODEL: old field-level place change review table.

Status: historical compatibility only, not the active review workflow.

How it worked:
- Early public catalog change review stored one row per proposed field change in
  `place_change_reviews`.
- Rows contained `city_id`, `place_id`, `field_name`, old/new value, reason,
  confidence/trust metadata and pending/reviewed status.

Why it is legacy:
- Active admin endpoint `/admin/place-change-reviews/*` does NOT read this table.
- Active service `services/place_change_review_service.py` reads
  `models.review_queue_item.ReviewQueueItem` with:
    - `field_name = "place_change"`
    - `status = "open"`
    - structured `payload` with changes and `before_public` snapshot.

Replacement / source of truth:
- `models.review_queue_item.ReviewQueueItem`
- `services.place_change_review_service`

Rules:
- Do not use this model in new routers, services, tests or scripts.
- Do not create new rows here for active moderation.
- Keep the model registered only so historical migrations/schema and old data are
  understandable and test metadata can still create the legacy table.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class PlaceChangeReview(Base):
    """Legacy row model for the pre-ReviewQueueItem place change review flow."""

    __tablename__ = "place_change_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    old_value: Mapped[dict[str, object] | list[object] | str | int | float | bool | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    new_value: Mapped[dict[str, object] | list[object] | str | int | float | bool | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="import", index=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
