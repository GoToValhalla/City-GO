"""add admin read snapshot tables

models/admin_read_snapshot.py defines AdminOverviewSnapshot
(admin_overview_snapshots), CityQualitySnapshot (admin_city_quality_snapshots)
and BacklogQueueSnapshot (backlog_queue_snapshots) as plain Table objects,
but no Alembic migration ever created them. They were only ever created at
runtime by scripts/bootstrap_admin_read_models.py (Table.create(checkfirst=True),
called from POST /admin/read-models/refresh and from the scheduled
admin-read-model-refresh.yml workflow before scripts/refresh_admin_read_models.py
runs). Every GET read path through services/admin_read_model_v2.py already
falls back to a live builder on any SQLAlchemyError, so a missing table never
surfaces as a broken admin page — but refresh_all()'s write path (_store,
_store_queue_rows) has no such fallback, so an environment where bootstrap
never ran (or partially failed) hits
"relation admin_overview_snapshots does not exist" the first time the
scheduled refresh job writes to it, failing that workflow with no
admin-visible warning.

These are opportunistic cache tables (see ARCHITECTURE_INVARIANTS.md
"Snapshot Freshness"), not participants in the ORM mapper registry, and
carry no foreign keys into business data. Creating them here does not change
import, readiness, or publication logic — it only makes their existence a
durable migration guarantee instead of a best-effort runtime side effect.
Idempotent via checkfirst (a production database may already have any subset
of these tables from the old bootstrap path).

Revision ID: 9719aa508caa
Revises: f0c0c48aa12a
Create Date: 2026-07-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "9719aa508caa"
down_revision = "f0c0c48aa12a"
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
    existing_tables = set(inspector.get_table_names())
    json_type = _json_type()

    if "admin_overview_snapshots" not in existing_tables:
        op.create_table(
            "admin_overview_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("payload", json_type, nullable=False),
            sa.Column("computed_at", sa.DateTime(), nullable=False),
            sa.Column("stale_after", sa.DateTime(), nullable=True),
            sa.Column("is_dirty", sa.Boolean(), nullable=False),
            sa.Column("source_version", sa.String(length=64), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_admin_overview_snapshots_computed_at"), "admin_overview_snapshots", ["computed_at"], unique=False)
        op.create_index(op.f("ix_admin_overview_snapshots_stale_after"), "admin_overview_snapshots", ["stale_after"], unique=False)
        op.create_index(op.f("ix_admin_overview_snapshots_is_dirty"), "admin_overview_snapshots", ["is_dirty"], unique=False)

    if "admin_city_quality_snapshots" not in existing_tables:
        op.create_table(
            "admin_city_quality_snapshots",
            sa.Column("city_id", sa.Integer(), nullable=False),
            sa.Column("readiness_score", sa.Integer(), nullable=False),
            sa.Column("places_total", sa.Integer(), nullable=False),
            sa.Column("review_universe_total", sa.Integer(), nullable=False),
            sa.Column("manual_review_total", sa.Integer(), nullable=False),
            sa.Column("auto_excluded_total", sa.Integer(), nullable=False),
            sa.Column("route_candidate_total", sa.Integer(), nullable=False),
            sa.Column("route_ready_total", sa.Integer(), nullable=False),
            sa.Column("route_blockers_total", sa.Integer(), nullable=False),
            sa.Column("primary_blocker", sa.String(length=64), nullable=True),
            sa.Column("blockers", json_type, nullable=False),
            sa.Column("computed_at", sa.DateTime(), nullable=True),
            sa.Column("stale_after", sa.DateTime(), nullable=True),
            sa.Column("is_dirty", sa.Boolean(), nullable=False),
            sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
            sa.PrimaryKeyConstraint("city_id"),
        )
        op.create_index(op.f("ix_admin_city_quality_snapshots_computed_at"), "admin_city_quality_snapshots", ["computed_at"], unique=False)
        op.create_index(op.f("ix_admin_city_quality_snapshots_stale_after"), "admin_city_quality_snapshots", ["stale_after"], unique=False)
        op.create_index(op.f("ix_admin_city_quality_snapshots_is_dirty"), "admin_city_quality_snapshots", ["is_dirty"], unique=False)

    if "backlog_queue_snapshots" not in existing_tables:
        op.create_table(
            "backlog_queue_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("scope_type", sa.String(length=32), nullable=False),
            sa.Column("scope_id", sa.String(length=128), nullable=True),
            sa.Column("queue_code", sa.String(length=64), nullable=False),
            sa.Column("reason_code", sa.String(length=64), nullable=True),
            sa.Column("count", sa.Integer(), nullable=False),
            sa.Column("sample_place_ids", json_type, nullable=False),
            sa.Column("computed_at", sa.DateTime(), nullable=False),
            sa.Column("stale_after", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("scope_type", "scope_id", "queue_code", "reason_code", name="uq_backlog_queue_snapshot_scope_queue_reason"),
        )
        op.create_index("ix_backlog_queue_snapshot_scope", "backlog_queue_snapshots", ["scope_type", "scope_id"], unique=False)
        op.create_index("ix_backlog_queue_snapshot_queue", "backlog_queue_snapshots", ["queue_code", "reason_code"], unique=False)
        op.create_index(op.f("ix_backlog_queue_snapshots_computed_at"), "backlog_queue_snapshots", ["computed_at"], unique=False)
        op.create_index(op.f("ix_backlog_queue_snapshots_stale_after"), "backlog_queue_snapshots", ["stale_after"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "backlog_queue_snapshots" in existing_tables:
        op.drop_table("backlog_queue_snapshots")
    if "admin_city_quality_snapshots" in existing_tables:
        op.drop_table("admin_city_quality_snapshots")
    if "admin_overview_snapshots" in existing_tables:
        op.drop_table("admin_overview_snapshots")
