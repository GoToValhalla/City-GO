"""route generation diagnostics tables

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_generation_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("request_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("algorithm_version", sa.String(64), nullable=False),
        sa.Column("total_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eligible_candidates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_places", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_generation_runs_city_id", "route_generation_runs", ["city_id"])
    op.create_index("ix_route_generation_runs_created_at", "route_generation_runs", ["created_at"])

    op.create_table(
        "route_generation_candidates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("generation_run_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("is_eligible", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("selected", sa.Boolean(), nullable=False),
        sa.Column("rejection_reasons", sa.JSON(), nullable=True),
        sa.Column("selection_reasons", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["generation_run_id"], ["route_generation_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_route_generation_candidates_run_id",
        "route_generation_candidates",
        ["generation_run_id"],
    )
    op.create_index(
        "ix_route_generation_candidates_place_id",
        "route_generation_candidates",
        ["place_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_route_generation_candidates_place_id", table_name="route_generation_candidates")
    op.drop_index("ix_route_generation_candidates_run_id", table_name="route_generation_candidates")
    op.drop_table("route_generation_candidates")
    op.drop_index("ix_route_generation_runs_created_at", table_name="route_generation_runs")
    op.drop_index("ix_route_generation_runs_city_id", table_name="route_generation_runs")
    op.drop_table("route_generation_runs")
