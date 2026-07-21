"""Фоновые admin-операции: адреса, enrichment, bulk."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AdminOperation(Base):
    __tablename__ = "admin_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operation_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True, default="pending")
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    city_slug: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    place_ids: Mapped[list[int] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    result: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
