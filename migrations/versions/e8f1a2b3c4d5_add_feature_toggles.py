"""add feature toggles table

Revision ID: e8f1a2b3c4d5
Revises: c1f4e7a9d2b3
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f1a2b3c4d5"
down_revision: Union[str, None] = "c1f4e7a9d2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "feature_toggles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("scope_id", sa.String(length=128), nullable=True),
        sa.Column("value_bool", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("updated_by", sa.String(length=255), nullable=True),
        sa.Column("change_reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "scope_id", "key", name="uq_feature_toggle_scope_key"),
    )
    op.create_index("ix_feature_toggles_key", "feature_toggles", ["key"])
    op.create_index("ix_feature_toggles_scope", "feature_toggles", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_feature_toggles_scope", table_name="feature_toggles")
    op.drop_index("ix_feature_toggles_key", table_name="feature_toggles")
    op.drop_table("feature_toggles")
