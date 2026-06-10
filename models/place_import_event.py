from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class PlaceImportEvent(Base):
    __tablename__ = "place_import_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, index=True, nullable=False)
    total: Mapped[int] = mapped_column(Integer, nullable=False)
    created: Mapped[int] = mapped_column(Integer, nullable=False)
    updated: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, nullable=False)
    invalid: Mapped[int] = mapped_column(Integer, nullable=False)
    city_slugs: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    errors: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"))
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
