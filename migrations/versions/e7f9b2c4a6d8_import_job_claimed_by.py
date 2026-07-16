"""city_admin_import_jobs: claimed_by column for atomic worker claim

Independent code review of d4e8a1f6b3c9 found the worker claim was not
atomic: FOR UPDATE SKIP LOCKED selected a queued row but only committed a
worker_job_claimed log entry, leaving the row itself status=queued,
started_at=NULL until the runner got around to its own queued->running
write — releasing the row lock in between let a second worker claim the
same row. The fix (services/admin_city_import_job_service.py::
claim_queued_job) performs the queued->running transition, started_at,
and worker identity write in the SAME transaction as the row lock, before
it commits. This migration adds the column that identity is stored in.

Revision ID: e7f9b2c4a6d8
Revises: d4e8a1f6b3c9
Create Date: 2026-07-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "e7f9b2c4a6d8"
down_revision = "d4e8a1f6b3c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("city_admin_import_jobs")}
    if "claimed_by" not in columns:
        op.add_column("city_admin_import_jobs", sa.Column("claimed_by", sa.String(length=128), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("city_admin_import_jobs")}
    if "claimed_by" in columns:
        with op.batch_alter_table("city_admin_import_jobs") as batch_op:
            batch_op.drop_column("claimed_by")
