"""add source_observations.processing_outcome

Revision ID: c3d5e7f9a1b3
Revises: f1a2b3c4d5e7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d5e7f9a1b3"
down_revision: Union[str, None] = "f1a2b3c4d5e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("source_observations") as batch_op:
        batch_op.add_column(sa.Column("processing_outcome", sa.String(64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("source_observations") as batch_op:
        batch_op.drop_column("processing_outcome")
