from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class Category(Base):
    """Управляемая категория City GO; пользовательские категории создаются через admin API."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    icon: Mapped[str | None] = mapped_column(String(100))
    color_token: Mapped[str] = mapped_column(String(100), default="category-default", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_catalog_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_route_eligible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_default_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_spam_category: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    default_visit_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    indoor_default: Mapped[bool | None] = mapped_column(Boolean)
    outdoor_default: Mapped[bool | None] = mapped_column(Boolean)
    user_name: Mapped[str | None] = mapped_column(String(255))
    admin_name: Mapped[str | None] = mapped_column(String(255))
    route_policy: Mapped[str] = mapped_column(String(32), default="manual_review", nullable=False, index=True)
    route_contexts: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), default=list, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    parent = relationship("Category", remote_side=[id], back_populates="children")
    children = relationship("Category", back_populates="parent", order_by="Category.sort_order")
    places = relationship("Place", back_populates="category_ref")

    @property
    def display_name(self) -> str:
        return self.user_name or self.name or self.admin_name or "Категория без названия"
