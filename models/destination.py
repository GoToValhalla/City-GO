"""Destination-first geographic/catalog entities (v1)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from db.base import Base


class Destination(Base):
    __tablename__ = "destinations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_type: Mapped[str] = mapped_column(String(64), nullable=False, default="city", index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("destinations.id"), nullable=True, index=True)
    legacy_city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    boundary: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    launch_status: Mapped[str] = mapped_column(String(64), nullable=False, default="draft", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    readiness_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    parent = relationship("Destination", remote_side="Destination.id", back_populates="children")
    children = relationship("Destination", back_populates="parent")
    scopes = relationship("DestinationScope", back_populates="destination")
    memberships = relationship("DestinationPlaceMembership", back_populates="destination")


class DestinationScope(Base):
    __tablename__ = "destination_scopes"
    __table_args__ = (UniqueConstraint("destination_id", "code", name="uq_destination_scope_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(64), nullable=False, default="all", index=True)
    import_strategy: Mapped[str] = mapped_column(String(64), nullable=False, default="single_bbox")
    bbox: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    polygon: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    import_profile: Mapped[str] = mapped_column(String(64), nullable=False, default="tourist_core")
    is_walkable_cluster: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    last_imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    destination = relationship("Destination", back_populates="scopes")


class DestinationPlaceMembership(Base):
    __tablename__ = "destination_place_memberships"
    __table_args__ = (
        UniqueConstraint("place_id", "destination_id", name="uq_place_destination_membership"),
        Index("ix_dpm_destination_hidden", "destination_id", "is_hidden"),
        Index("ix_dpm_destination_place", "destination_id", "place_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_id: Mapped[int | None] = mapped_column(ForeignKey("destination_scopes.id"), nullable=True, index=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    assignment_type: Mapped[str] = mapped_column(String(64), nullable=False, default="legacy_city")
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    source: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    destination = relationship("Destination", back_populates="memberships")
    place = relationship("Place", back_populates="destination_memberships")


class DestinationMembershipConflict(Base):
    """Placeholder for ambiguous overlapping scope assignments."""

    __tablename__ = "destination_membership_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id", ondelete="CASCADE"), nullable=False, index=True)
    destination_id: Mapped[int] = mapped_column(ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False, index=True)
    scope_ids: Mapped[list[int] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    reason: Mapped[str] = mapped_column(String(128), nullable=False, default="overlapping_scopes")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
