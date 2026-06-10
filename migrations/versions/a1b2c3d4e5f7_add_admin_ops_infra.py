"""admin ops infra: system_logs, product_events, admin_operations, place fields

Revision ID: a1b2c3d4e5f7
Revises: f9a2b3c4d5e6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f9a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "system_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("message", sa.String(2000), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("city_slug", sa.String(100), nullable=True),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("route_id", sa.String(100), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("environment", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_module", "system_logs", ["module"])
    op.create_index("ix_system_logs_created_at", "system_logs", ["created_at"])

    op.create_table(
        "product_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("city_slug", sa.String(100), nullable=True),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_events_event_type", "product_events", ["event_type"])
    op.create_index("ix_product_events_created_at", "product_events", ["created_at"])

    op.create_table(
        "admin_operations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("operation_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("city_slug", sa.String(100), nullable=True),
        sa.Column("place_ids", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_operations_status", "admin_operations", ["status"])

    for col, typ in (
        ("address_source", sa.String(64)),
        ("route_exclusion_reason", sa.String(1000)),
        ("admin_comment", sa.String(2000)),
    ):
        op.add_column("places", sa.Column(col, typ, nullable=True))
    op.add_column("places", sa.Column("address_confidence", sa.Float(), nullable=True))
    op.add_column("places", sa.Column("address_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    for col in ("address_updated_at", "address_confidence", "admin_comment", "route_exclusion_reason", "address_source"):
        op.drop_column("places", col)
    op.drop_index("ix_admin_operations_status", table_name="admin_operations")
    op.drop_table("admin_operations")
    op.drop_index("ix_product_events_created_at", table_name="product_events")
    op.drop_index("ix_product_events_event_type", table_name="product_events")
    op.drop_table("product_events")
    op.drop_index("ix_system_logs_created_at", table_name="system_logs")
    op.drop_index("ix_system_logs_module", table_name="system_logs")
    op.drop_index("ix_system_logs_level", table_name="system_logs")
    op.drop_table("system_logs")
