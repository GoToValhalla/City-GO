"""Add lease/heartbeat, attempt count, and worker identity to admin_operations.

lease_generation is a fencing token: every successful claim/reclaim
increments it, and every subsequent heartbeat or terminal write from that
worker must match the generation it was handed at claim time. This makes a
worker's own in-flight writes a no-op once another worker has reclaimed the
row (its generation is now stale), which is what makes lease renewal safe
without ever holding a transaction open across runner execution.

Revision ID: d3f8a1c6b4e9
Revises: c8a91d4e7f20
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from services.migration_column_guard import drop_column_if_owned, ensure_column

revision = "d3f8a1c6b4e9"
down_revision = "c8a91d4e7f20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ensure_column(
        bind,
        revision=revision,
        table="admin_operations",
        column=sa.Column("claimed_at", sa.DateTime(), nullable=True),
    )
    ensure_column(
        bind,
        revision=revision,
        table="admin_operations",
        column=sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
    )
    ensure_column(
        bind,
        revision=revision,
        table="admin_operations",
        column=sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
    )
    ensure_column(
        bind,
        revision=revision,
        table="admin_operations",
        column=sa.Column("worker_id", sa.String(length=128), nullable=True),
    )
    ensure_column(
        bind,
        revision=revision,
        table="admin_operations",
        column=sa.Column("lease_generation", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    drop_column_if_owned(bind, revision=revision, table="admin_operations", column="lease_generation")
    drop_column_if_owned(bind, revision=revision, table="admin_operations", column="worker_id")
    drop_column_if_owned(bind, revision=revision, table="admin_operations", column="attempt_count")
    drop_column_if_owned(bind, revision=revision, table="admin_operations", column="lease_expires_at")
    drop_column_if_owned(bind, revision=revision, table="admin_operations", column="claimed_at")
