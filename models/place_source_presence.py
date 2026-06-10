from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PlaceSourcePresence(Base):
    __tablename__ = "place_source_presence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int | None] = mapped_column(ForeignKey("places.id"), nullable=True, index=True)
    source_observation_id: Mapped[int | None] = mapped_column(ForeignKey("source_observations.id"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False, default="osm")
    source_external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    consecutive_missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_missing_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    presence_status: Mapped[str] = mapped_column(String(64), nullable=False, default="active_in_source")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
