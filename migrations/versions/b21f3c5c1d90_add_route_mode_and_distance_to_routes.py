"""add_route_mode_and_distance_to_routes

Revision ID: b21f3c5c1d90
Revises: 9c8e4b1a2f10
Create Date: 2026-04-03 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b21f3c5c1d90"
down_revision: Union[str, None] = "9c8e4b1a2f10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("routes", sa.Column("distance_km", sa.Float(), nullable=True))
    op.add_column(
        "routes",
        sa.Column(
            "route_mode",
            sa.String(length=50),
            nullable=False,
            server_default="walk",
        ),
    )


def downgrade() -> None:
    op.drop_column("routes", "route_mode")
    op.drop_column("routes", "distance_km")
