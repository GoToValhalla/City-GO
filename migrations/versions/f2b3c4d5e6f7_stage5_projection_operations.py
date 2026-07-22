"""Stage 5 projection operations and projection-only payloads.

Revision ID: f2b3c4d5e6f7
Revises: e1a2b3c4d5f6
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f2b3c4d5e6f7"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None

JSON = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("search_place_documents", sa.Column("is_catalog_visible", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index("ix_search_place_documents_is_catalog_visible", "search_place_documents", ["is_catalog_visible"])
    op.add_column("search_place_documents", sa.Column("public_payload", JSON, nullable=False, server_default=sa.text("'{}'")))
    op.add_column("routing_place_nodes", sa.Column("place_payload", JSON, nullable=False, server_default=sa.text("'{}'")))
    op.add_column("projection_rebuild_jobs", sa.Column("scope_key", sa.String(64), nullable=False, server_default="global"))
    op.add_column("projection_rebuild_jobs", sa.Column("generation", sa.String(64), nullable=True))
    op.add_column("projection_rebuild_jobs", sa.Column("expected_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projection_rebuild_jobs", sa.Column("actual_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("projection_rebuild_jobs", sa.Column("is_complete", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("projection_rebuild_jobs", sa.Column("actor", sa.String(255), nullable=True))
    op.add_column("projection_rebuild_jobs", sa.Column("source", sa.String(64), nullable=True))
    op.add_column("projection_rebuild_jobs", sa.Column("audit_context", JSON, nullable=False, server_default=sa.text("'{}'")))
    for column in ("scope_key", "generation", "is_complete"):
        op.create_index(f"ix_projection_rebuild_jobs_{column}", "projection_rebuild_jobs", [column])


def downgrade() -> None:
    for column in ("is_complete", "generation", "scope_key"):
        op.drop_index(f"ix_projection_rebuild_jobs_{column}", table_name="projection_rebuild_jobs")
    for column in ("audit_context", "source", "actor", "is_complete", "actual_count", "expected_count", "generation", "scope_key"):
        op.drop_column("projection_rebuild_jobs", column)
    op.drop_column("routing_place_nodes", "place_payload")
    op.drop_column("search_place_documents", "public_payload")
    op.drop_index("ix_search_place_documents_is_catalog_visible", table_name="search_place_documents")
    op.drop_column("search_place_documents", "is_catalog_visible")
