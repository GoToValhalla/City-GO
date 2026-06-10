"""add_place_data_quality_fields

Revision ID: 7a0f1f2c9d31
Revises: f6c2d9a1b4e8
Create Date: 2026-05-28 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a0f1f2c9d31"
down_revision: Union[str, None] = "f6c2d9a1b4e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("source", sa.String(length=100), nullable=True))
    op.add_column("places", sa.Column("source_url", sa.String(length=1000), nullable=True))
    op.add_column("places", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("places", sa.Column("last_verified_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "last_verified_at")
    op.drop_column("places", "confidence")
    op.drop_column("places", "source_url")
    op.drop_column("places", "source")
