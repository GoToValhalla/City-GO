"""add data quality foundation

Revision ID: b7c2d4e6f8a0
Revises: a6c1d8e9f304
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "b7c2d4e6f8a0"
down_revision = "a6c1d8e9f304"
branch_labels = None
depends_on = None

Json = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "data_quality_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("issue_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="open"),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("evidence", Json, nullable=True),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("fingerprint", name="uq_data_quality_issue_fingerprint"),
    )
    _indexes("data_quality_issues", ("place_id", "city_id", "issue_type", "status", "severity", "fingerprint"))
    op.create_table(
        "data_quality_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("issue_id", sa.Integer(), sa.ForeignKey("data_quality_issues.id"), nullable=False),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("candidate_type", sa.String(64), nullable=False),
        sa.Column("proposed_patch", Json, nullable=False),
        sa.Column("evidence", Json, nullable=True),
        sa.Column("source", sa.String(64), nullable=False, server_default="deterministic"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.Column("decided_by", sa.String(255), nullable=True),
        sa.Column("audit_ref", sa.String(255), nullable=True),
        sa.Column("rollback_ref", sa.String(255), nullable=True),
        sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("fingerprint", name="uq_data_quality_candidate_fingerprint"),
    )
    _indexes("data_quality_candidates", ("issue_id", "place_id", "city_id", "candidate_type", "status", "fingerprint"))


def downgrade() -> None:
    _drop_indexes("data_quality_candidates", ("issue_id", "place_id", "city_id", "candidate_type", "status", "fingerprint"))
    op.drop_table("data_quality_candidates")
    _drop_indexes("data_quality_issues", ("place_id", "city_id", "issue_type", "status", "severity", "fingerprint"))
    op.drop_table("data_quality_issues")


def _indexes(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def _drop_indexes(table: str, columns: tuple[str, ...]) -> None:
    for column in columns:
        op.drop_index(f"ix_{table}_{column}", table_name=table)
