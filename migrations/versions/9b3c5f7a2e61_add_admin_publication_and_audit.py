"""add admin publication flags and audit log

Revision ID: 9b3c5f7a2e61
Revises: 2b7f6a4d9c10
Create Date: 2026-06-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "9b3c5f7a2e61"
down_revision: Union[str, None] = "2b7f6a4d9c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    jsonb_type = postgresql.JSONB().with_variant(sa.JSON(), "sqlite")
    op.add_column("places", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("places", sa.Column("is_visible_in_catalog", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("places", sa.Column("is_route_eligible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("places", sa.Column("is_searchable", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("places", sa.Column("publication_status", sa.String(length=32), nullable=False, server_default="published"))
    op.add_column("places", sa.Column("publication_comment", sa.String(length=1000), nullable=True))
    op.add_column("places", sa.Column("published_at", sa.DateTime(), nullable=True))
    op.add_column("places", sa.Column("unpublished_at", sa.DateTime(), nullable=True))
    op.create_index("ix_places_is_published", "places", ["is_published"])
    op.create_index("ix_places_is_visible_in_catalog", "places", ["is_visible_in_catalog"])
    op.create_index("ix_places_is_route_eligible", "places", ["is_route_eligible"])
    op.create_index("ix_places_is_searchable", "places", ["is_searchable"])
    op.create_index("ix_places_publication_status", "places", ["publication_status"])

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=True),
        sa.Column("old_value", jsonb_type, nullable=True),
        sa.Column("new_value", jsonb_type, nullable=True),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_entity_type", "admin_audit_logs", ["entity_type"])
    op.create_index("ix_admin_audit_logs_entity_id", "admin_audit_logs", ["entity_id"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_entity_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_entity_type", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
    op.drop_index("ix_places_publication_status", table_name="places")
    op.drop_index("ix_places_is_searchable", table_name="places")
    op.drop_index("ix_places_is_route_eligible", table_name="places")
    op.drop_index("ix_places_is_visible_in_catalog", table_name="places")
    op.drop_index("ix_places_is_published", table_name="places")
    op.drop_column("places", "unpublished_at")
    op.drop_column("places", "published_at")
    op.drop_column("places", "publication_comment")
    op.drop_column("places", "publication_status")
    op.drop_column("places", "is_searchable")
    op.drop_column("places", "is_route_eligible")
    op.drop_column("places", "is_visible_in_catalog")
    op.drop_column("places", "is_published")
