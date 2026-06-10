"""add_place_verification_tasks

Revision ID: b9d2c1f0a882
Revises: a37d9108c2b5
Create Date: 2026-05-28 17:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9d2c1f0a882"
down_revision: Union[str, None] = "a37d9108c2b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "place_verification_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_verification_tasks_place_id", "place_verification_tasks", ["place_id"])
    op.create_index("ix_place_verification_tasks_status", "place_verification_tasks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_place_verification_tasks_status", table_name="place_verification_tasks")
    op.drop_index("ix_place_verification_tasks_place_id", table_name="place_verification_tasks")
    op.drop_table("place_verification_tasks")
