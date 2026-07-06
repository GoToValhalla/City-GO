"""Stored sanitized debug reports from public/admin UI."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from db.base import Base


class DebugReport(Base):
    __tablename__ = "debug_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    environment: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    app_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    screen: Mapped[str] = mapped_column(String(64), nullable=False, default="unknown", index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False, default="info", index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, default="other", index=True)
    city_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    destination_slug: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    place_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    route_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    request_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    user_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    frontend_state: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    request_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    response_summary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    response_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    debug_trace: Mapped[dict[str, object] | list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    warnings: Mapped[list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    reason_codes: Mapped[list[object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    linked_entities: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    browser: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    location_context: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    backend_context: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    sanitized_payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False, default=dict)
    telegram_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    telegram_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
