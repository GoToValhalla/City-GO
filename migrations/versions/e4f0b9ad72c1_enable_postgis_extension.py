"""record_geospatial_query_portability

Revision ID: e4f0b9ad72c1
Revises: d3a7f8840e12
Create Date: 2026-05-26 00:04:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "e4f0b9ad72c1"
down_revision: Union[str, None] = "d3a7f8840e12"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("SELECT 1")


def downgrade() -> None:
    pass
