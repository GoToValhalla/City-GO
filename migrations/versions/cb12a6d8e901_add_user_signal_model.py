"""add_user_signal_model

Revision ID: cb12a6d8e901
Revises: 7a0f1f2c9d31
Create Date: 2026-05-28 13:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "cb12a6d8e901"
down_revision: Union[str, None] = "7a0f1f2c9d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "user_signals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(length=100), nullable=False),
        sa.Column("signal_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("payload", jsonb_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_signals_user_id", "user_signals", ["user_id"])
    op.create_index("ix_user_signals_signal_type", "user_signals", ["signal_type"])
    op.create_index("ix_user_signals_entity", "user_signals", ["entity_type", "entity_id"])


def downgrade() -> None:
    op.drop_index("ix_user_signals_entity", table_name="user_signals")
    op.drop_index("ix_user_signals_signal_type", table_name="user_signals")
    op.drop_index("ix_user_signals_user_id", table_name="user_signals")
    op.drop_table("user_signals")
