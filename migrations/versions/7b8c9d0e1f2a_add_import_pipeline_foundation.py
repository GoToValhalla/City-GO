"""add import pipeline foundation: 7b8c9d0e1f2a -> 6c4a8d1e2f90"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
revision: str = "7b8c9d0e1f2a"
down_revision: Union[str, None] = "6c4a8d1e2f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
_json = JSONB().with_variant(JSON(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "import_job_steps",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(64), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("counters", _json, nullable=True), sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["city_admin_import_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    _indexes("import_job_steps", ("id", "job_id", "step_name", "status"))
    _place_field_confidence()
    _photo_candidates()
    _review_queue()


def downgrade() -> None:
    op.drop_table("review_queue_items")
    op.drop_table("place_photo_candidates")
    op.drop_table("place_field_confidence")
    tuple(op.drop_index(name, table_name="import_job_steps") for name in (
        "ix_import_job_steps_status", "ix_import_job_steps_step_name", "ix_import_job_steps_job_id",
    ))
    op.drop_table("import_job_steps")


def _place_field_confidence() -> None:
    op.create_table(
        "place_field_confidence",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=False), sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("confidence_level", sa.String(32), nullable=False), sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("freshness_status", sa.String(32), nullable=False), sa.Column("conflict_status", sa.String(32), nullable=False),
        sa.Column("is_manual_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("raw_value", _json, nullable=True), sa.Column("updated_by", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "field_name", name="uq_place_field_confidence"),
    )
    _indexes("place_field_confidence", ("id", "place_id", "field_name", "confidence_level", "source_type", "freshness_status", "conflict_status", "is_manual_verified"))


def _photo_candidates() -> None:
    op.create_table(
        "place_photo_candidates",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(2000), nullable=False), sa.Column("thumbnail_url", sa.String(2000), nullable=True),
        sa.Column("source_type", sa.String(64), nullable=False), sa.Column("source_url", sa.String(2000), nullable=True),
        sa.Column("match_type", sa.String(32), nullable=False), sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_primary_candidate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.String(255), nullable=True), sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "image_url", name="uq_place_photo_candidate_url"),
    )
    _indexes("place_photo_candidates", ("id", "place_id", "source_type", "match_type", "status"))


def _review_queue() -> None:
    op.create_table(
        "review_queue_items",
        sa.Column("id", sa.Integer(), nullable=False), sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False), sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(100), nullable=False), sa.Column("reason", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False), sa.Column("status", sa.String(32), nullable=False),
        sa.Column("payload", _json, nullable=True), sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True), sa.Column("resolution", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["city_admin_import_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "field_name", "reason", "status", name="uq_review_item_open"),
    )
    _indexes("review_queue_items", ("id", "city_id", "place_id", "job_id", "field_name", "reason", "severity", "status"))


def _indexes(table: str, columns: tuple[str, ...]) -> None:
    tuple(op.create_index(f"ix_{table}_{column}", table, [column]) for column in columns)
