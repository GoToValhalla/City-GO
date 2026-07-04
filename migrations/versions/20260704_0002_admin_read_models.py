"""admin read model snapshots

Revision ID: a4f6d8e2c913
Revises: fb7e3c2a91d4
Create Date: 2026-07-04 14:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a4f6d8e2c913"
down_revision: Union[str, None] = "fb7e3c2a91d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_overview_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("stale_after", sa.DateTime(), nullable=True),
        sa.Column("is_dirty", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source_version", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_admin_overview_snapshots_computed_at", "admin_overview_snapshots", ["computed_at"])
    op.create_index("ix_admin_overview_snapshots_stale_after", "admin_overview_snapshots", ["stale_after"])
    op.create_index("ix_admin_overview_snapshots_is_dirty", "admin_overview_snapshots", ["is_dirty"])

    op.create_table(
        "city_quality_snapshots",
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), primary_key=True, nullable=False),
        sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("places_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_universe_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_review_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_excluded_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route_candidate_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route_ready_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("route_blockers_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("primary_blocker", sa.String(length=64), nullable=True),
        sa.Column("blockers", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("computed_at", sa.DateTime(), nullable=True),
        sa.Column("stale_after", sa.DateTime(), nullable=True),
        sa.Column("is_dirty", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_city_quality_snapshots_computed_at", "city_quality_snapshots", ["computed_at"])
    op.create_index("ix_city_quality_snapshots_stale_after", "city_quality_snapshots", ["stale_after"])
    op.create_index("ix_city_quality_snapshots_is_dirty", "city_quality_snapshots", ["is_dirty"])

    op.create_table(
        "backlog_queue_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("queue_code", sa.String(length=64), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sample_place_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.Column("stale_after", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("scope_type", "scope_id", "queue_code", "reason_code", name="uq_backlog_queue_snapshot_scope_queue_reason"),
    )
    op.create_index("ix_backlog_queue_snapshot_scope", "backlog_queue_snapshots", ["scope_type", "scope_id"])
    op.create_index("ix_backlog_queue_snapshot_queue", "backlog_queue_snapshots", ["queue_code", "reason_code"])
    op.create_index("ix_backlog_queue_snapshots_computed_at", "backlog_queue_snapshots", ["computed_at"])
    op.create_index("ix_backlog_queue_snapshots_stale_after", "backlog_queue_snapshots", ["stale_after"])


def downgrade() -> None:
    op.drop_index("ix_backlog_queue_snapshots_stale_after", table_name="backlog_queue_snapshots")
    op.drop_index("ix_backlog_queue_snapshots_computed_at", table_name="backlog_queue_snapshots")
    op.drop_index("ix_backlog_queue_snapshot_queue", table_name="backlog_queue_snapshots")
    op.drop_index("ix_backlog_queue_snapshot_scope", table_name="backlog_queue_snapshots")
    op.drop_table("backlog_queue_snapshots")

    op.drop_index("ix_city_quality_snapshots_is_dirty", table_name="city_quality_snapshots")
    op.drop_index("ix_city_quality_snapshots_stale_after", table_name="city_quality_snapshots")
    op.drop_index("ix_city_quality_snapshots_computed_at", table_name="city_quality_snapshots")
    op.drop_table("city_quality_snapshots")

    op.drop_index("ix_admin_overview_snapshots_is_dirty", table_name="admin_overview_snapshots")
    op.drop_index("ix_admin_overview_snapshots_stale_after", table_name="admin_overview_snapshots")
    op.drop_index("ix_admin_overview_snapshots_computed_at", table_name="admin_overview_snapshots")
    op.drop_table("admin_overview_snapshots")
