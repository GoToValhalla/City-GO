"""add index on places.category

Revision ID: c3d4e5f6a7b8
Revises: b2d4f6a8c3e5
"""

from __future__ import annotations

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "b2d4f6a8c3e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.create_index("ix_places_category", ["category"])


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_index("ix_places_category")
