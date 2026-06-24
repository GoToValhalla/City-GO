"""add admin alert lifecycle

Revision ID: c8a1d4e7f920
Revises: fb7e3c2a91d4
"""

import sqlalchemy as sa
from alembic import op

revision = "c8a1d4e7f920"
down_revision = "fb7e3c2a91d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_log_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("acknowledged_by", sa.String(255), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_admin_alerts_source_log_id", "admin_alerts", ["source_log_id"], unique=True)
    op.create_index("ix_admin_alerts_status", "admin_alerts", ["status"])


def downgrade() -> None:
    op.drop_index("ix_admin_alerts_status", table_name="admin_alerts")
    op.drop_index("ix_admin_alerts_source_log_id", table_name="admin_alerts")
    op.drop_table("admin_alerts")
