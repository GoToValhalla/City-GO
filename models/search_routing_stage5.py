from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class SearchPlaceDocument(Base):
    """Search/catalog read projection built from published snapshots."""

    __tablename__ = "search_place_documents"
    __table_args__ = (
        UniqueConstraint("place_id", "locale", "source_snapshot_version", name="uq_search_place_document_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    source_snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    locale: Mapped[str] = mapped_column(String(16), default="default", nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    searchable_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tags_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_search_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    ranking_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh", nullable=False, index=True)
    built_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RoutingPlaceNode(Base):
    """Routing read projection built from published snapshots."""

    __tablename__ = "routing_place_nodes"
    __table_args__ = (
        UniqueConstraint("place_id", "route_policy", "source_snapshot_version", name="uq_routing_place_node_snapshot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    source_snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    route_policy: Mapped[str] = mapped_column(String(64), default="city_walking", nullable=False, index=True)
    average_visit_duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_route_visible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    quality_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh", nullable=False, index=True)
    built_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class RouteCandidateSet(Base):
    """Precomputed routing candidates for city/profile/policy."""

    __tablename__ = "route_candidate_sets"
    __table_args__ = (
        UniqueConstraint("city_id", "profile", "route_policy", "source_snapshot_version", name="uq_route_candidate_set_scope"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)
    profile: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    route_policy: Mapped[str] = mapped_column(String(64), default="city_walking", nullable=False, index=True)
    source_snapshot_version: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    candidate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB().with_variant(JSON(), "sqlite"), nullable=False)
    freshness_status: Mapped[str] = mapped_column(String(32), default="fresh", nullable=False, index=True)
    built_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class ProjectionRebuildJob(Base):
    """Operational job for rebuilding read projections."""

    __tablename__ = "projection_rebuild_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    projection_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    city_id: Mapped[int | None] = mapped_column(ForeignKey("cities.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    source_snapshot_version: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rebuilt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
