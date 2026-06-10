"""add_user_id_to_route_build_events

Revision ID: c2b8a9e1d4f3
Revises: b9d2c1f0a882
Create Date: 2026-05-28 18:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2b8a9e1d4f3"
down_revision: Union[str, None] = "b9d2c1f0a882"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("route_build_events", sa.Column("user_id", sa.String(length=100), nullable=True))
    op.create_index("ix_route_build_events_user_id", "route_build_events", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_route_build_events_user_id", table_name="route_build_events")
    op.drop_column("route_build_events", "user_id")
