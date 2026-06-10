"""add_place_status

Revision ID: d1f8a7c2b904
Revises: cb12a6d8e901
Create Date: 2026-05-28 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1f8a7c2b904"
down_revision: Union[str, None] = "cb12a6d8e901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "places",
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.create_index("ix_places_status", "places", ["status"])
    with op.batch_alter_table("places") as batch_op:
        batch_op.alter_column("status", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_places_status", table_name="places")
    op.drop_column("places", "status")
