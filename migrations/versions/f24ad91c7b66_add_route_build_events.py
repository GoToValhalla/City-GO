"""add_route_build_events

Revision ID: f24ad91c7b66
Revises: d1f8a7c2b904
Create Date: 2026-05-28 15:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f24ad91c7b66"
down_revision: Union[str, None] = "d1f8a7c2b904"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "route_build_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("city_id", sa.String(length=100), nullable=True),
        sa.Column("total_places", sa.Integer(), nullable=False),
        sa.Column("total_minutes", sa.Integer(), nullable=False),
        sa.Column("quality_score", sa.Float(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("has_warnings", sa.Boolean(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("warnings", jsonb_type, nullable=True),
        sa.Column("quality_breakdown", jsonb_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_build_events_route_id", "route_build_events", ["route_id"])
    op.create_index("ix_route_build_events_source", "route_build_events", ["source"])
    op.create_index("ix_route_build_events_city_id", "route_build_events", ["city_id"])


def downgrade() -> None:
    op.drop_index("ix_route_build_events_city_id", table_name="route_build_events")
    op.drop_index("ix_route_build_events_source", table_name="route_build_events")
    op.drop_index("ix_route_build_events_route_id", table_name="route_build_events")
    op.drop_table("route_build_events")
