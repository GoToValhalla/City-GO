"""import schema compatibility for OSM collecting_places

Revision ID: a1c2d3e4f5b6
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

from alembic import op

revision = "a1c2d3e4f5b6"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from services.import_pipeline.schema_compat import ensure_import_pipeline_schema

    ensure_import_pipeline_schema(op.get_bind().engine)


def downgrade() -> None:
    # Compatibility repair migration: no destructive downgrade.
    return
