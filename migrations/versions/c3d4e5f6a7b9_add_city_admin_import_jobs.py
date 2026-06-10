"""city admin import jobs

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "city_admin_import_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("scopes_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scopes_succeeded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("places_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("places_saved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_city_admin_import_jobs_city_id", "city_admin_import_jobs", ["city_id"])
    op.create_index("ix_city_admin_import_jobs_status", "city_admin_import_jobs", ["status"])
    op.create_index("ix_city_admin_import_jobs_created_at", "city_admin_import_jobs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_city_admin_import_jobs_created_at", table_name="city_admin_import_jobs")
    op.drop_index("ix_city_admin_import_jobs_status", table_name="city_admin_import_jobs")
    op.drop_index("ix_city_admin_import_jobs_city_id", table_name="city_admin_import_jobs")
    op.drop_table("city_admin_import_jobs")
