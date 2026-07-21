"""Add user_signals.dedup_key with a unique index for atomic feedback dedup.

Revision ID: e1a2b3c4d5f6
Revises: d3f8a1c6b4e9
Create Date: 2026-07-21
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from services.migration_column_guard import drop_column_if_owned, drop_index_if_owned, ensure_column, ensure_index

revision = "e1a2b3c4d5f6"
down_revision = "d3f8a1c6b4e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    ensure_column(
        bind,
        revision=revision,
        table="user_signals",
        column=sa.Column("dedup_key", sa.String(length=64), nullable=True),
    )
    ensure_index(
        bind,
        revision=revision,
        index_name="uq_user_signals_dedup_key",
        table="user_signals",
        columns=["dedup_key"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    drop_index_if_owned(bind, revision=revision, table="user_signals", index_name="uq_user_signals_dedup_key")
    drop_column_if_owned(bind, revision=revision, table="user_signals", column="dedup_key")
