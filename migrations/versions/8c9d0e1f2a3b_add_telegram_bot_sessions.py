"""add telegram bot sessions

Revision ID: 8c9d0e1f2a3b
Revises: 7b8c9d0e1f2a
Create Date: 2026-06-23 08:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "8c9d0e1f2a3b"
down_revision: str | None = "7b8c9d0e1f2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _jsonb() -> sa.types.TypeEngine:
    return postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "bot_sessions",
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=128), nullable=True),
        sa.Column("selected_city_slug", sa.String(length=64), nullable=True),
        sa.Column("current_flow", sa.String(length=64), nullable=True),
        sa.Column("last_message_id", sa.Integer(), nullable=True),
        sa.Column("nav_stack", _jsonb(), nullable=False, server_default="[]"),
        sa.Column("short_ids", _jsonb(), nullable=False, server_default="{}"),
        sa.Column("route_session", _jsonb(), nullable=True),
        sa.Column("favorites", _jsonb(), nullable=False, server_default='{"places": [], "routes": []}'),
        sa.Column("last_location", _jsonb(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("telegram_user_id"),
    )
    op.create_index(op.f("ix_bot_sessions_telegram_user_id"), "bot_sessions", ["telegram_user_id"], unique=False)
    op.create_index(op.f("ix_bot_sessions_selected_city_slug"), "bot_sessions", ["selected_city_slug"], unique=False)
    op.create_index(op.f("ix_bot_sessions_current_flow"), "bot_sessions", ["current_flow"], unique=False)

    op.create_table(
        "bot_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("city_slug", sa.String(length=64), nullable=True),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.String(length=128), nullable=True),
        sa.Column("payload", _jsonb(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bot_events_id"), "bot_events", ["id"], unique=False)
    op.create_index(op.f("ix_bot_events_telegram_user_id"), "bot_events", ["telegram_user_id"], unique=False)
    op.create_index(op.f("ix_bot_events_event_type"), "bot_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_bot_events_city_slug"), "bot_events", ["city_slug"], unique=False)
    op.create_index(op.f("ix_bot_events_created_at"), "bot_events", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bot_events_created_at"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_city_slug"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_event_type"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_telegram_user_id"), table_name="bot_events")
    op.drop_index(op.f("ix_bot_events_id"), table_name="bot_events")
    op.drop_table("bot_events")

    op.drop_index(op.f("ix_bot_sessions_current_flow"), table_name="bot_sessions")
    op.drop_index(op.f("ix_bot_sessions_selected_city_slug"), table_name="bot_sessions")
    op.drop_index(op.f("ix_bot_sessions_telegram_user_id"), table_name="bot_sessions")
    op.drop_table("bot_sessions")
