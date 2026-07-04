"""Read-model snapshot tables for admin and platform performance gates.

These are intentionally plain SQLAlchemy Table objects, not ORM mappers.
Read-model snapshots must not participate in the application mapper registry.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from db.base import Base

Json = JSONB().with_variant(JSON(), "sqlite")

AdminOverviewSnapshot = Table(
    "admin_overview_snapshots",
    Base.metadata,
    Column("id", Integer, primary_key=True, default=1),
    Column("payload", Json, nullable=False, default=dict),
    Column("computed_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
    Column("stale_after", DateTime, nullable=True, index=True),
    Column("is_dirty", Boolean, default=True, nullable=False, index=True),
    Column("source_version", String(64), nullable=True),
    extend_existing=True,
)

CityQualitySnapshot = Table(
    "admin_city_quality_snapshots",
    Base.metadata,
    Column("city_id", Integer, ForeignKey("cities.id"), primary_key=True),
    Column("readiness_score", Integer, default=0, nullable=False),
    Column("places_total", Integer, default=0, nullable=False),
    Column("review_universe_total", Integer, default=0, nullable=False),
    Column("manual_review_total", Integer, default=0, nullable=False),
    Column("auto_excluded_total", Integer, default=0, nullable=False),
    Column("route_candidate_total", Integer, default=0, nullable=False),
    Column("route_ready_total", Integer, default=0, nullable=False),
    Column("route_blockers_total", Integer, default=0, nullable=False),
    Column("primary_blocker", String(64), nullable=True),
    Column("blockers", Json, nullable=False, default=dict),
    Column("computed_at", DateTime, nullable=True, index=True),
    Column("stale_after", DateTime, nullable=True, index=True),
    Column("is_dirty", Boolean, default=True, nullable=False, index=True),
    extend_existing=True,
)

BacklogQueueSnapshot = Table(
    "backlog_queue_snapshots",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("scope_type", String(32), nullable=False),
    Column("scope_id", String(128), nullable=True),
    Column("queue_code", String(64), nullable=False),
    Column("reason_code", String(64), nullable=True),
    Column("count", Integer, default=0, nullable=False),
    Column("sample_place_ids", Json, nullable=False, default=list),
    Column("computed_at", DateTime, default=datetime.utcnow, nullable=False, index=True),
    Column("stale_after", DateTime, nullable=True, index=True),
    UniqueConstraint("scope_type", "scope_id", "queue_code", "reason_code", name="uq_backlog_queue_snapshot_scope_queue_reason"),
    Index("ix_backlog_queue_snapshot_scope", "scope_type", "scope_id"),
    Index("ix_backlog_queue_snapshot_queue", "queue_code", "reason_code"),
    extend_existing=True,
)
