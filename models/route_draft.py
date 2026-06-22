from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class RouteDraft(Base):
    __tablename__ = "route_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    session_token: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    route_status: Mapped[str] = mapped_column(String(32), nullable=False, default="partial")
    start_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_type: Mapped[str] = mapped_column(String(32), nullable=False, default="city_center")
    budget_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=120)
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    random_seed: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_category_slugs: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list)
    category_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="none")
    user_removed_place_ids: Mapped[list[int]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list)
    warnings: Mapped[list[dict[str, object]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list)
    edit_history: Mapped[list[dict[str, object]]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    points = relationship("RouteDraftPoint", back_populates="draft", cascade="all, delete-orphan")
    city = relationship("City")


class RouteDraftPoint(Base):
    __tablename__ = "route_draft_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    draft_id: Mapped[int] = mapped_column(ForeignKey("route_drafts.id"), nullable=False, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1, index=True)
    user_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inserted_by_user: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    replacement_of_place_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    walk_minutes_from_prev: Mapped[int | None] = mapped_column(Integer, nullable=True)
    walk_minutes_to_next: Mapped[int | None] = mapped_column(Integer, nullable=True)
    visit_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=35)
    open_status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    draft = relationship("RouteDraft", back_populates="points")
    place = relationship("Place")
