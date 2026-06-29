"""add import job changes

Revision ID: d0e1f2a3b4c5
Revises: c8d4e6f9a102
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d0e1f2a3b4c5"
down_revision = "c8d4e6f9a102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    json_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.create_table(
        "city_admin_import_job_changes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=True),
        sa.Column("external_source_id", sa.String(length=255), nullable=True),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("place_title", sa.String(length=500), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("before_json", json_type, nullable=True),
        sa.Column("after_json", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["city_admin_import_jobs.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, cols in _indexes().items():
        op.create_index(name, "city_admin_import_job_changes", cols)


def downgrade() -> None:
    for name in _indexes():
        op.drop_index(name, table_name="city_admin_import_job_changes")
    op.drop_table("city_admin_import_job_changes")


def _indexes() -> dict[str, list[str]]:
    return {
        "ix_city_admin_import_job_changes_id": ["id"],
        "ix_city_admin_import_job_changes_job_id": ["job_id"],
        "ix_city_admin_import_job_changes_city_id": ["city_id"],
        "ix_city_admin_import_job_changes_place_id": ["place_id"],
        "ix_city_admin_import_job_changes_external_source_id": ["external_source_id"],
        "ix_city_admin_import_job_changes_change_type": ["change_type"],
        "ix_city_admin_import_job_changes_created_at": ["created_at"],
        "ix_import_job_changes_job_type": ["job_id", "change_type"],
        "ix_import_job_changes_city_type": ["city_id", "change_type"],
    }
