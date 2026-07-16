"""add import_tile_runs table

CITYGO-320: persistent per-tile execution state for tiled OSM imports
(CITYGO-317's deterministic tile planner, CITYGO-319's tiled import
orchestration). One row per (scope, tile_id) tracks queued/running/
completed/failed/skipped status so a crashed or interrupted tiled import
can resume from the first unfinished tile instead of restarting the
whole scope. tile_id is deterministic (services/osm_tile_planner.py),
so re-planning the same bbox/config on resume always maps back to the
same rows.

This table has no foreign key into publication/place data and is not
read by any existing import, publication, or review code path — it is
purely additive, dark-launched storage for the new tiled orchestrator.

Revision ID: cc90ca369082
Revises: 9719aa508caa
Create Date: 2026-07-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "cc90ca369082"
down_revision = "9719aa508caa"
branch_labels = None
depends_on = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "import_tile_runs" in inspector.get_table_names():
        return

    op.create_table(
        "import_tile_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("city_admin_import_job_id", sa.Integer(), nullable=True),
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("tile_id", sa.String(length=64), nullable=False),
        sa.Column("planner_version", sa.String(length=64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("total_tiles", sa.Integer(), nullable=False),
        sa.Column("south", sa.Float(), nullable=False),
        sa.Column("west", sa.Float(), nullable=False),
        sa.Column("north", sa.Float(), nullable=False),
        sa.Column("east", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failure_reason", sa.String(length=2000), nullable=True),
        sa.Column("counters", _json_type(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scope_id"], ["city_import_scopes.id"]),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope_id", "tile_id", name="uq_import_tile_runs_scope_tile"),
    )
    op.create_index(op.f("ix_import_tile_runs_scope_id"), "import_tile_runs", ["scope_id"], unique=False)
    op.create_index(op.f("ix_import_tile_runs_city_admin_import_job_id"), "import_tile_runs", ["city_admin_import_job_id"], unique=False)
    op.create_index(op.f("ix_import_tile_runs_batch_id"), "import_tile_runs", ["batch_id"], unique=False)
    op.create_index(op.f("ix_import_tile_runs_tile_id"), "import_tile_runs", ["tile_id"], unique=False)
    op.create_index(op.f("ix_import_tile_runs_status"), "import_tile_runs", ["status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "import_tile_runs" in inspector.get_table_names():
        op.drop_table("import_tile_runs")
