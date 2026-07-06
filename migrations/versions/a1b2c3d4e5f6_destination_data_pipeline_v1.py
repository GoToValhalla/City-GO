"""destination data pipeline v1

Revision ID: a1b2c3d4e5f6
Revises: f7a8b9c0d1e2
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destination_data_pipeline_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("triggered_by", sa.String(length=255), server_default="admin", nullable=False),
        sa.Column("trigger_source", sa.String(length=64), server_default="admin_workspace", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("stage", sa.String(length=64), server_default="preparing", nullable=False),
        sa.Column("scope_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("counters", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("errors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("dry_run", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("mode", sa.String(length=32), server_default="full", nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("destination_id", "idempotency_key", name="uq_destination_pipeline_idempotency"),
    )
    op.create_index("ix_destination_pipeline_destination_id", "destination_data_pipeline_runs", ["destination_id"])
    op.create_index("ix_destination_pipeline_status", "destination_data_pipeline_runs", ["status"])
    op.create_index("ix_destination_pipeline_stage", "destination_data_pipeline_runs", ["stage"])
    op.create_index("ix_destination_pipeline_created_at", "destination_data_pipeline_runs", ["created_at"])
    op.create_index("ix_destination_pipeline_idempotency_key", "destination_data_pipeline_runs", ["idempotency_key"])


def downgrade() -> None:
    op.drop_table("destination_data_pipeline_runs")
