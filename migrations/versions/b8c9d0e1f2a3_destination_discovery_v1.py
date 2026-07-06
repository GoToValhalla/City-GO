"""Destination discovery jobs and candidates.

Revision ID: b8c9d0e1f2a3
Revises: a1b2c3d4e5f6
"""

from alembic import op
import sqlalchemy as sa

revision = "b8c9d0e1f2a3"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_discovery_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("region_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), server_default="deterministic", nullable=False),
        sa.Column("region_snapshot", sa.JSON(), nullable=True),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("progress_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result_summary", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destination_discovery_jobs_status", "destination_discovery_jobs", ["status"])
    op.create_index("ix_destination_discovery_jobs_region_id", "destination_discovery_jobs", ["region_id"])

    op.create_table(
        "destination_discovery_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("provider", sa.String(length=64), server_default="deterministic", nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("native_name", sa.String(length=255), nullable=True),
        sa.Column("english_name", sa.String(length=255), nullable=True),
        sa.Column("destination_type", sa.String(length=64), server_default="city", nullable=False),
        sa.Column("parent_region", sa.String(length=255), nullable=True),
        sa.Column("center_lat", sa.Float(), nullable=True),
        sa.Column("center_lng", sa.Float(), nullable=True),
        sa.Column("bbox_json", sa.JSON(), nullable=True),
        sa.Column("polygon_json", sa.JSON(), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("confidence_json", sa.JSON(), nullable=True),
        sa.Column("ranking_score", sa.Float(), server_default="0", nullable=False),
        sa.Column("tier", sa.String(length=32), server_default="unknown", nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=True),
        sa.Column("existing_match_json", sa.JSON(), nullable=True),
        sa.Column("scope_overlaps_json", sa.JSON(), nullable=True),
        sa.Column("recommended_scopes_json", sa.JSON(), nullable=True),
        sa.Column("reasons_json", sa.JSON(), nullable=True),
        sa.Column("created_destination_slug", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["destination_discovery_jobs.id"]),
        sa.UniqueConstraint("job_id", "external_id", name="uq_discovery_job_external"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destination_discovery_candidates_job_id", "destination_discovery_candidates", ["job_id"])
    op.create_index("ix_destination_discovery_candidates_tier", "destination_discovery_candidates", ["tier"])
    op.create_index("ix_destination_discovery_candidates_created_destination_slug", "destination_discovery_candidates", ["created_destination_slug"])


def downgrade() -> None:
    op.drop_table("destination_discovery_candidates")
    op.drop_table("destination_discovery_jobs")
