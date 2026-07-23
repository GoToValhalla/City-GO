"""Field/place review queue for import and enrichment pipeline."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class ReviewQueueItem(Base):
    __tablename__ = "review_queue_items"
    __table_args__ = (
        # Enforces "at most one open item per logical problem" at the
        # database level. The previous uq_review_item_open constraint
        # included `status` in its key, so it did not constrain the open
        # side at all and it collided on the resolved side: two rows
        # sharing (place_id, field_name, reason) that both reach
        # status="resolved" (legitimate historical audit entries from two
        # separate import/enrichment cycles) violated that constraint. A
        # partial unique index scoped to open/pending rows only enforces
        # the real invariant and leaves resolved history unconstrained.
        Index(
            "uq_review_queue_items_open_identity",
            "place_id", "field_name", "reason",
            unique=True,
            postgresql_where=text("status IN ('open', 'pending')"),
            sqlite_where=text("status IN ('open', 'pending')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    job_id: Mapped[int | None] = mapped_column(ForeignKey("city_admin_import_jobs.id"), nullable=True, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
