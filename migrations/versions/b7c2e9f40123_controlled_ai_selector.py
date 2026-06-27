"""controlled ai selector

Revision ID: b7c2e9f40123
Revises: a6c1d8e9f304
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c2e9f40123"
down_revision = "a6c1d8e9f304"
branch_labels = None
depends_on = None

JSON = sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("SET LOCAL lock_timeout = '30s'"))
        bind.execute(sa.text("SET LOCAL statement_timeout = '5min'"))

    op.create_table(
        "ai_budget_ledgers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(16), nullable=False),
        sa.Column("period_key", sa.String(32), nullable=False),
        sa.Column("reserved_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spent_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("scope", "period_key", name="uq_ai_budget_ledgers_scope_period"),
    )
    op.create_index("ix_ai_budget_ledgers_id", "ai_budget_ledgers", ["id"])
    op.create_index("ix_ai_budget_ledgers_scope", "ai_budget_ledgers", ["scope"])
    op.create_index("ix_ai_budget_ledgers_period_key", "ai_budget_ledgers", ["period_key"])

    op.create_table(
        "ai_budget_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_run_id", sa.Integer(), nullable=True),
        sa.Column("actor", sa.String(255), nullable=False, server_default="admin"),
        sa.Column("status", sa.String(32), nullable=False, server_default="reserved"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("day_key", sa.String(16), nullable=False),
        sa.Column("month_key", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("failure_policy", sa.String(32), nullable=False, server_default="spend_reserved_on_unknown"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_budget_reservations_id", "ai_budget_reservations", ["id"])
    op.create_index("ix_ai_budget_reservations_task_run_id", "ai_budget_reservations", ["task_run_id"])
    op.create_index("ix_ai_budget_reservations_actor", "ai_budget_reservations", ["actor"])
    op.create_index("ix_ai_budget_reservations_status", "ai_budget_reservations", ["status"])
    op.create_index("ix_ai_budget_reservations_day_key", "ai_budget_reservations", ["day_key"])
    op.create_index("ix_ai_budget_reservations_month_key", "ai_budget_reservations", ["month_key"])
    op.create_index("ix_ai_budget_reservations_expires_at", "ai_budget_reservations", ["expires_at"])

    op.create_table(
        "ai_task_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("provider_key", sa.String(64), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False, server_default="shadow"),
        sa.Column("status", sa.String(32), nullable=False, server_default="created"),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("actor", sa.String(255), nullable=False, server_default="admin"),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("review_queue_item_id", sa.Integer(), sa.ForeignKey("review_queue_items.id"), nullable=True),
        sa.Column("budget_reservation_id", sa.Integer(), sa.ForeignKey("ai_budget_reservations.id"), nullable=True),
        sa.Column("input_tokens_estimate", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens_limit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Float(), nullable=True),
        sa.Column("prompt_snapshot", JSON, nullable=True),
        sa.Column("output_snapshot", JSON, nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.String(2000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_ai_task_runs_id", "ai_task_runs", ["id"])
    op.create_index("ix_ai_task_runs_task_type", "ai_task_runs", ["task_type"])
    op.create_index("ix_ai_task_runs_provider_key", "ai_task_runs", ["provider_key"])
    op.create_index("ix_ai_task_runs_mode", "ai_task_runs", ["mode"])
    op.create_index("ix_ai_task_runs_status", "ai_task_runs", ["status"])
    op.create_index("ix_ai_task_runs_actor", "ai_task_runs", ["actor"])
    op.create_index("ix_ai_task_runs_city_id", "ai_task_runs", ["city_id"])
    op.create_index("ix_ai_task_runs_place_id", "ai_task_runs", ["place_id"])
    op.create_index("ix_ai_task_runs_review_queue_item_id", "ai_task_runs", ["review_queue_item_id"])
    op.create_index("ix_ai_task_runs_budget_reservation_id", "ai_task_runs", ["budget_reservation_id"])
    op.create_index("ix_ai_task_runs_error_code", "ai_task_runs", ["error_code"])
    op.create_index("ix_ai_task_runs_created_at", "ai_task_runs", ["created_at"])

    op.create_table(
        "ai_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("task_run_id", sa.Integer(), sa.ForeignKey("ai_task_runs.id"), nullable=False),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=True),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("review_queue_item_id", sa.Integer(), sa.ForeignKey("review_queue_items.id"), nullable=True),
        sa.Column("candidate_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("proposed_payload", JSON, nullable=False),
        sa.Column("evidence_payload", JSON, nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=False, server_default="ai"),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("resolution_note", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ai_candidates_id", "ai_candidates", ["id"])
    op.create_index("ix_ai_candidates_task_run_id", "ai_candidates", ["task_run_id"])
    op.create_index("ix_ai_candidates_city_id", "ai_candidates", ["city_id"])
    op.create_index("ix_ai_candidates_place_id", "ai_candidates", ["place_id"])
    op.create_index("ix_ai_candidates_review_queue_item_id", "ai_candidates", ["review_queue_item_id"])
    op.create_index("ix_ai_candidates_candidate_type", "ai_candidates", ["candidate_type"])
    op.create_index("ix_ai_candidates_status", "ai_candidates", ["status"])
    op.create_index("ix_ai_candidates_created_at", "ai_candidates", ["created_at"])


def downgrade() -> None:
    op.drop_table("ai_candidates")
    op.drop_table("ai_task_runs")
    op.drop_table("ai_budget_reservations")
    op.drop_table("ai_budget_ledgers")
