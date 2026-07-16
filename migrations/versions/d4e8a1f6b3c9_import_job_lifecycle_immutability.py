"""city_admin_import_jobs: immutable lifecycle (previous_job_id, lifecycle_flag)

Production Job #1 corruption: a terminal row was reset back to queued and
reused by a later, unrelated worker run, mixing timelines/counters from
different executions. The application fix (see
services/admin_city_import_job_service.py) makes every launch/retry insert
a brand-new row instead of reusing one. This migration adds the columns
that new lifecycle needs:

- previous_job_id: self-referencing FK forming the append-only retry chain
  (NULL for a city's first launch).
- lifecycle_flag: set only by the legacy-repair command
  (data/scripts/repair_import_job_lifecycle.py) to mark a pre-existing row
  whose contradictory state (e.g. status=queued with started_at/finished_at
  already set) cannot be safely reconstructed into a truthful terminal
  status.
- a partial unique index enforcing at most one active (queued/running) row
  per city_id, matching the application-level guarantee _enqueue_job
  already provides under FOR UPDATE.

No existing rows are deleted or rewritten by this migration.

Revision ID: d4e8a1f6b3c9
Revises: b3e7f1a4c8d2
Create Date: 2026-07-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e8a1f6b3c9"
down_revision = "b3e7f1a4c8d2"
branch_labels = None
depends_on = None

ACTIVE_UNIQUE_NAME = "uq_city_admin_import_jobs_active_city"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("city_admin_import_jobs")}

    if "previous_job_id" not in columns:
        with op.batch_alter_table("city_admin_import_jobs") as batch_op:
            batch_op.add_column(sa.Column("previous_job_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_city_admin_import_jobs_previous_job_id",
                "city_admin_import_jobs",
                ["previous_job_id"],
                ["id"],
            )
    if "lifecycle_flag" not in columns:
        op.add_column("city_admin_import_jobs", sa.Column("lifecycle_flag", sa.String(length=32), nullable=True))

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("city_admin_import_jobs")}
    if "ix_city_admin_import_jobs_previous_job_id" not in existing_indexes:
        op.create_index(
            op.f("ix_city_admin_import_jobs_previous_job_id"),
            "city_admin_import_jobs",
            ["previous_job_id"],
            unique=False,
        )
    if "ix_city_admin_import_jobs_lifecycle_flag" not in existing_indexes:
        op.create_index(
            op.f("ix_city_admin_import_jobs_lifecycle_flag"),
            "city_admin_import_jobs",
            ["lifecycle_flag"],
            unique=False,
        )
    if ACTIVE_UNIQUE_NAME not in existing_indexes:
        op.create_index(
            ACTIVE_UNIQUE_NAME,
            "city_admin_import_jobs",
            ["city_id"],
            unique=True,
            postgresql_where=sa.text("status IN ('queued', 'running')"),
            sqlite_where=sa.text("status IN ('queued', 'running')"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {ix["name"] for ix in inspector.get_indexes("city_admin_import_jobs")}

    if ACTIVE_UNIQUE_NAME in existing_indexes:
        op.drop_index(ACTIVE_UNIQUE_NAME, table_name="city_admin_import_jobs")
    if "ix_city_admin_import_jobs_lifecycle_flag" in existing_indexes:
        op.drop_index(op.f("ix_city_admin_import_jobs_lifecycle_flag"), table_name="city_admin_import_jobs")
    if "ix_city_admin_import_jobs_previous_job_id" in existing_indexes:
        op.drop_index(op.f("ix_city_admin_import_jobs_previous_job_id"), table_name="city_admin_import_jobs")

    columns = {col["name"] for col in inspector.get_columns("city_admin_import_jobs")}
    if "lifecycle_flag" in columns:
        with op.batch_alter_table("city_admin_import_jobs") as batch_op:
            batch_op.drop_column("lifecycle_flag")
    if "previous_job_id" in columns:
        with op.batch_alter_table("city_admin_import_jobs") as batch_op:
            batch_op.drop_constraint("fk_city_admin_import_jobs_previous_job_id", type_="foreignkey")
            batch_op.drop_column("previous_job_id")
