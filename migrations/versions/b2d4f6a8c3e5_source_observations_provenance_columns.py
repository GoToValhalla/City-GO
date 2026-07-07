"""add missing source_observations provenance columns

Revision ID: b2d4f6a8c3e5
Revises: a1c2d3e4f5b6
"""

from __future__ import annotations

from alembic import op

revision = "b2d4f6a8c3e5"
down_revision = "a1c2d3e4f5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from services.import_pipeline.schema_compat import ensure_import_pipeline_schema

    ensure_import_pipeline_schema(op.get_bind().engine)


def downgrade() -> None:
    # Compatibility repair migration: no destructive downgrade.
    return
