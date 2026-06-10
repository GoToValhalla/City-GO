"""import job pipeline fields

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

_json = JSONB().with_variant(JSON(), "sqlite")

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("city_admin_import_jobs", sa.Column("current_step", sa.String(64), nullable=False, server_default="created"))
    op.add_column("city_admin_import_jobs", sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("city_admin_import_jobs", sa.Column("processed_items", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("city_admin_import_jobs", sa.Column("successful_items", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("city_admin_import_jobs", sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("city_admin_import_jobs", sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("city_admin_import_jobs", sa.Column("step_details", _json, nullable=True))
    op.add_column("city_admin_import_jobs", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    op.add_column("cities", sa.Column("slug_aliases", _json, nullable=True))


def downgrade() -> None:
    op.drop_column("cities", "slug_aliases")
    op.drop_column("city_admin_import_jobs", "cancelled_at")
    op.drop_column("city_admin_import_jobs", "step_details")
    op.drop_column("city_admin_import_jobs", "retry_count")
    op.drop_column("city_admin_import_jobs", "failed_items")
    op.drop_column("city_admin_import_jobs", "successful_items")
    op.drop_column("city_admin_import_jobs", "processed_items")
    op.drop_column("city_admin_import_jobs", "total_items")
    op.drop_column("city_admin_import_jobs", "current_step")
