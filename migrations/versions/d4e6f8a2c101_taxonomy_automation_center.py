"""taxonomy automation center

Revision ID: d4e6f8a2c101
Revises: c8a1d4e7f920
"""

from alembic import op
import sqlalchemy as sa

revision = "d4e6f8a2c101"
down_revision = "c8a1d4e7f920"
branch_labels = None
depends_on = None

JSON = sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        # Production deploys must fail with a useful error instead of waiting
        # indefinitely when a runtime transaction holds a DDL lock.
        bind.execute(sa.text("SET LOCAL lock_timeout = '30s'"))
        bind.execute(sa.text("SET LOCAL statement_timeout = '10min'"))

    with op.batch_alter_table("categories") as batch:
        batch.add_column(sa.Column("description", sa.Text(), nullable=True))
        batch.add_column(sa.Column("parent_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("icon", sa.String(100), nullable=True))
        batch.add_column(sa.Column("color_token", sa.String(100), nullable=False, server_default="category-default"))
        batch.add_column(sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.add_column(sa.Column("default_visit_duration_minutes", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("indoor_default", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("outdoor_default", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("user_name", sa.String(255), nullable=True))
        batch.add_column(sa.Column("admin_name", sa.String(255), nullable=True))
        batch.add_column(sa.Column("route_policy", sa.String(32), nullable=False, server_default="manual_review"))
        batch.add_column(sa.Column("route_contexts", JSON, nullable=False, server_default="[]"))
        batch.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        batch.create_foreign_key("fk_categories_parent", "categories", ["parent_id"], ["id"])
        batch.create_index("ix_categories_parent_id", ["parent_id"])
        batch.create_index("ix_categories_sort_order", ["sort_order"])
        batch.create_index("ix_categories_route_policy", ["route_policy"])

    op.create_table("taxonomy_mappings",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_key", sa.String(128), nullable=False), sa.Column("source_value", sa.String(255), nullable=False),
        sa.Column("target_category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"), sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("conditions", JSON, nullable=False),
        sa.Column("conditions_hash", sa.String(64), nullable=False, server_default="-"), sa.Column("fallback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("comment", sa.String(1000)), sa.Column("created_by", sa.String(255), nullable=False, server_default="system"),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source", "source_key", "source_value", "conditions_hash", name="uq_taxonomy_mapping_match"))
    op.create_table("taxonomy_decisions",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id")), sa.Column("mapping_id", sa.Integer(), sa.ForeignKey("taxonomy_mappings.id")),
        sa.Column("decision_type", sa.String(32), nullable=False), sa.Column("confidence", sa.Float(), nullable=False), sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("warnings", JSON, nullable=False), sa.Column("alternatives", JSON, nullable=False), sa.Column("old_category_id", sa.Integer()),
        sa.Column("actor", sa.String(255), nullable=False), sa.Column("batch_id", sa.String(64)), sa.Column("reversible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False))
    op.create_table("taxonomy_conflicts",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("conflict_type", sa.String(64), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("source", sa.String(64)),
        sa.Column("confidence", sa.Float()), sa.Column("current_category_id", sa.Integer(), sa.ForeignKey("categories.id")),
        sa.Column("recommended_category_id", sa.Integer(), sa.ForeignKey("categories.id")), sa.Column("details", JSON, nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("resolution", JSON), sa.Column("resolved_by", sa.String(255)),
        sa.Column("resolved_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("quality_rules",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("code", sa.String(100), nullable=False, unique=True),
        sa.Column("name_ru", sa.String(255), nullable=False), sa.Column("severity", sa.String(16), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False), sa.Column("parameters", JSON, nullable=False), sa.Column("auto_fix_available", sa.Boolean(), nullable=False),
        sa.Column("blocking_publication", sa.Boolean(), nullable=False), sa.Column("blocking_route_eligibility", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False))
    op.create_table("quality_issues",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("rule_id", sa.Integer(), sa.ForeignKey("quality_rules.id"), nullable=False),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False), sa.Column("fingerprint", sa.String(128), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False), sa.Column("status", sa.String(24), nullable=False), sa.Column("details", JSON, nullable=False),
        sa.Column("fixed_at", sa.DateTime()), sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("rule_id", "place_id", "fingerprint", name="uq_quality_issue_fingerprint"))
    op.create_table("taxonomy_bulk_batches",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("idempotency_key", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("actor", sa.String(255), nullable=False), sa.Column("filters", JSON, nullable=False),
        sa.Column("preview", JSON, nullable=False), sa.Column("result", JSON), sa.Column("rollback_result", JSON), sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("applied_at", sa.DateTime()), sa.Column("rolled_back_at", sa.DateTime()))
    op.create_table("workflow_operations",
        sa.Column("id", sa.String(64), primary_key=True), sa.Column("workflow", sa.String(100), nullable=False), sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(160), nullable=False, unique=True), sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.String(128)), sa.Column("status", sa.String(24), nullable=False), sa.Column("current_step", sa.String(100)),
        sa.Column("steps", JSON, nullable=False), sa.Column("payload", JSON, nullable=False), sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False), sa.Column("error_message", sa.Text()), sa.Column("actor", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False), sa.Column("finished_at", sa.DateTime()))


def downgrade() -> None:
    for table in ("workflow_operations", "taxonomy_bulk_batches", "quality_issues", "quality_rules", "taxonomy_conflicts", "taxonomy_decisions", "taxonomy_mappings"):
        op.drop_table(table)
    with op.batch_alter_table("categories") as batch:
        batch.drop_constraint("fk_categories_parent", type_="foreignkey")
        for index in ("ix_categories_route_policy", "ix_categories_sort_order", "ix_categories_parent_id"):
            batch.drop_index(index)
        for column in ("archived_at", "route_contexts", "route_policy", "admin_name", "user_name", "outdoor_default", "indoor_default", "default_visit_duration_minutes", "is_searchable", "sort_order", "color_token", "icon", "parent_id", "description"):
            batch.drop_column(column)
