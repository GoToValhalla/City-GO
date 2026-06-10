"""add_place_recommendation_fields

Revision ID: d3a7f8840e12
Revises: c7b36de91a2d
Create Date: 2026-05-25 23:58:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d3a7f8840e12"
down_revision: Union[str, None] = "c7b36de91a2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.add_column("places", sa.Column("opening_hours", jsonb_type, nullable=True))
    op.add_column("places", sa.Column("average_visit_duration_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "average_visit_duration_minutes")
    op.drop_column("places", "opening_hours")

