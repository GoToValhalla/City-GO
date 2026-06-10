"""add_place_import_events

Revision ID: a37d9108c2b5
Revises: f24ad91c7b66
Create Date: 2026-05-28 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a37d9108c2b5"
down_revision: Union[str, None] = "f24ad91c7b66"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "place_import_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("created", sa.Integer(), nullable=False),
        sa.Column("updated", sa.Integer(), nullable=False),
        sa.Column("skipped", sa.Integer(), nullable=False),
        sa.Column("invalid", sa.Integer(), nullable=False),
        sa.Column("city_slugs", jsonb_type, nullable=True),
        sa.Column("errors", jsonb_type, nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_import_events_dry_run", "place_import_events", ["dry_run"])


def downgrade() -> None:
    op.drop_index("ix_place_import_events_dry_run", table_name="place_import_events")
    op.drop_table("place_import_events")
