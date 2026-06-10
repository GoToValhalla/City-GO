"""add_telegram_user_contexts

Revision ID: f6c2d9a1b4e8
Revises: e4f0b9ad72c1
Create Date: 2026-05-26 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6c2d9a1b4e8"
down_revision: Union[str, None] = "e4f0b9ad72c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "telegram_user_contexts",
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("last_lat", sa.Float(), nullable=True),
        sa.Column("last_lng", sa.Float(), nullable=True),
        sa.Column("raw_address", sa.Text(), nullable=True),
        sa.Column("route_state", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(
        op.f("ix_telegram_user_contexts_user_id"),
        "telegram_user_contexts",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_telegram_user_contexts_user_id"),
        table_name="telegram_user_contexts",
    )
    op.drop_table("telegram_user_contexts")
