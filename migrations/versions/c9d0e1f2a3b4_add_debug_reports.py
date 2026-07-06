"""add debug reports

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-07 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

try:
    from sqlalchemy.dialects import postgresql
except Exception:  # pragma: no cover
    postgresql = None

revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if postgresql is not None and bind.dialect.name == "postgresql":
        return postgresql.JSONB()
    return sa.JSON()


def upgrade() -> None:
    json_type = _json_type()
    op.create_table(
        "debug_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=32), nullable=False, unique=True),
        sa.Column("environment", sa.String(length=64), nullable=True),
        sa.Column("app_version", sa.String(length=128), nullable=True),
        sa.Column("screen", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="info"),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="other"),
        sa.Column("city_slug", sa.String(length=120), nullable=True),
        sa.Column("destination_slug", sa.String(length=120), nullable=True),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("route_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("user_action", sa.Text(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("user_comment", sa.Text(), nullable=True),
        sa.Column("frontend_state", json_type, nullable=True),
        sa.Column("request_payload", json_type, nullable=True),
        sa.Column("response_summary", json_type, nullable=True),
        sa.Column("response_payload", json_type, nullable=True),
        sa.Column("debug_trace", json_type, nullable=True),
        sa.Column("warnings", json_type, nullable=True),
        sa.Column("reason_codes", json_type, nullable=True),
        sa.Column("linked_entities", json_type, nullable=True),
        sa.Column("browser", json_type, nullable=True),
        sa.Column("location_context", json_type, nullable=True),
        sa.Column("backend_context", json_type, nullable=True),
        sa.Column("sanitized_payload", json_type, nullable=False, server_default=sa.text("'{}'")),
        sa.Column("telegram_sent", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("telegram_error", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    for column in ("public_id", "environment", "screen", "severity", "category", "city_slug", "destination_slug", "place_id", "route_id", "request_id", "status", "created_at"):
        op.create_index(f"ix_debug_reports_{column}", "debug_reports", [column])


def downgrade() -> None:
    op.drop_table("debug_reports")
