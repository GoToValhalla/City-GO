"""add route sessions: 9d0e1f2a3b4c -> 8c9d0e1f2a3b"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "9d0e1f2a3b4c"
down_revision: Union[str, None] = "8c9d0e1f2a3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_json = JSONB().with_variant(JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "route_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("route_id", sa.Integer(), nullable=False),
        sa.Column("user_key", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("current_point_index", sa.Integer(), nullable=False),
        sa.Column("visited_point_indexes", _json, nullable=False),
        sa.Column("skipped_point_indexes", _json, nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_sessions_id", "route_sessions", ["id"])
    op.create_index("ix_route_sessions_route_id", "route_sessions", ["route_id"])
    op.create_index("ix_route_sessions_status", "route_sessions", ["status"])
    op.create_index("ix_route_sessions_user_key", "route_sessions", ["user_key"])

    op.create_table(
        "route_session_points",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("ordering_index", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("is_visited", sa.Boolean(), nullable=False),
        sa.Column("is_skipped", sa.Boolean(), nullable=False),
        sa.Column("visited_at", sa.DateTime(), nullable=True),
        sa.Column("skipped_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["route_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "ordering_index", name="uq_route_session_point_order"),
    )
    op.create_index("ix_route_session_points_id", "route_session_points", ["id"])
    op.create_index("ix_route_session_points_session_id", "route_session_points", ["session_id"])
    op.create_index("ix_route_session_points_place_id", "route_session_points", ["place_id"])
    op.create_index("ix_route_session_points_ordering_index", "route_session_points", ["ordering_index"])
    op.create_index("ix_route_session_points_is_visited", "route_session_points", ["is_visited"])
    op.create_index("ix_route_session_points_is_skipped", "route_session_points", ["is_skipped"])


def downgrade() -> None:
    op.drop_table("route_session_points")
    op.drop_index("ix_route_sessions_user_key", table_name="route_sessions")
    op.drop_index("ix_route_sessions_status", table_name="route_sessions")
    op.drop_index("ix_route_sessions_route_id", table_name="route_sessions")
    op.drop_index("ix_route_sessions_id", table_name="route_sessions")
    op.drop_table("route_sessions")
