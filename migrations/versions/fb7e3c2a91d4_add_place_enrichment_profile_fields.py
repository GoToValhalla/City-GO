"""add place enrichment profile fields

Revision ID: fb7e3c2a91d4
Revises: 9d0e1f2a3b4c
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fb7e3c2a91d4"
down_revision: Union[str, None] = "9d0e1f2a3b4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.add_column(sa.Column("website", sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("atmosphere", sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column("inside", sa.String(1000), nullable=True))
        batch_op.add_column(sa.Column("best_for", sa.String(1000), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_column("best_for")
        batch_op.drop_column("inside")
        batch_op.drop_column("atmosphere")
        batch_op.drop_column("phone")
        batch_op.drop_column("website")
