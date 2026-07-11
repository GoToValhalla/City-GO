"""Add source profile ownership to place source presence.

Revision ID: d4e6f8a0b2c4
Revises: c3d5e7f9a1b3
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "d4e6f8a0b2c4"
down_revision: str | None = "c3d5e7f9a1b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("place_source_presence") as batch_op:
        batch_op.add_column(sa.Column("source_profile", sa.String(length=64), nullable=True))
        batch_op.create_index(
            "ix_place_source_presence_source_profile",
            ["source_profile"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("place_source_presence") as batch_op:
        batch_op.drop_index("ix_place_source_presence_source_profile")
        batch_op.drop_column("source_profile")
