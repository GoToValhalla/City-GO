"""place card data refresh v1

Revision ID: e6a1b2c3d4f5
Revises: d0e1f2a3b4c5
Create Date: 2026-07-06 08:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "e6a1b2c3d4f5"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("places", sa.Column("internal_status", sa.String(length=32), server_default="active", nullable=False))
    op.add_column("places", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
    op.add_column("places", sa.Column("lineage", sa.JSON(), server_default=sa.text("'{}'"), nullable=False))
    op.add_column("places", sa.Column("last_enriched_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_places_internal_status"), "places", ["internal_status"], unique=False)

    op.create_table(
        "place_manual_overrides",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("override_value", sa.JSON(), nullable=True),
        sa.Column("set_by", sa.String(length=255), nullable=False, server_default="admin"),
        sa.Column("set_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_place_manual_overrides_id"), "place_manual_overrides", ["id"], unique=False)
    op.create_index(op.f("ix_place_manual_overrides_place_id"), "place_manual_overrides", ["place_id"], unique=False)
    op.create_index(op.f("ix_place_manual_overrides_field_name"), "place_manual_overrides", ["field_name"], unique=False)
    op.create_index(op.f("ix_place_manual_overrides_is_protected"), "place_manual_overrides", ["is_protected"], unique=False)

    op.create_table(
        "review_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("enrichment_task_id", sa.Integer(), nullable=True),
        sa.Column("proposed_diff", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False, server_default="system"),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("place_version_at_creation", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["enrichment_task_id"], ["enrichment_tasks.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_items_id"), "review_items", ["id"], unique=False)
    op.create_index(op.f("ix_review_items_place_id"), "review_items", ["place_id"], unique=False)
    op.create_index(op.f("ix_review_items_enrichment_task_id"), "review_items", ["enrichment_task_id"], unique=False)
    op.create_index(op.f("ix_review_items_status"), "review_items", ["status"], unique=False)
    op.create_index(op.f("ix_review_items_created_at"), "review_items", ["created_at"], unique=False)
    op.create_index(op.f("ix_review_items_source"), "review_items", ["source"], unique=False)
    op.create_index(op.f("ix_review_items_reason"), "review_items", ["reason"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_review_items_reason"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_source"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_created_at"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_status"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_enrichment_task_id"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_place_id"), table_name="review_items")
    op.drop_index(op.f("ix_review_items_id"), table_name="review_items")
    op.drop_table("review_items")

    op.drop_index(op.f("ix_place_manual_overrides_is_protected"), table_name="place_manual_overrides")
    op.drop_index(op.f("ix_place_manual_overrides_field_name"), table_name="place_manual_overrides")
    op.drop_index(op.f("ix_place_manual_overrides_place_id"), table_name="place_manual_overrides")
    op.drop_index(op.f("ix_place_manual_overrides_id"), table_name="place_manual_overrides")
    op.drop_table("place_manual_overrides")

    op.drop_index(op.f("ix_places_internal_status"), table_name="places")
    op.drop_column("places", "last_enriched_at")
    op.drop_column("places", "lineage")
    op.drop_column("places", "version")
    op.drop_column("places", "internal_status")
