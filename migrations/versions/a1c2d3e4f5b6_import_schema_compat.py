"""import schema compatibility for OSM collecting_places

Revision ID: a1c2d3e4f5b6
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import create_engine

revision = "a1c2d3e4f5b6"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from services.import_pipeline.schema_compat import ensure_import_pipeline_schema

    # ensure_import_pipeline_schema() opens its own connection and commits
    # incrementally as it goes — it must not share op.get_bind()'s connection,
    # which is inside Alembic's own open migration transaction on the same
    # session. Reusing that connection/engine here caused the two to contend
    # for locks on `places`/`source_observations` within the same DB session,
    # producing a reproducible local hang (idle-in-transaction + blocked
    # introspection query) every time this migration ran against a real
    # multi-scope database. A genuinely separate engine avoids that.
    isolated_engine = create_engine(op.get_bind().engine.url)
    try:
        ensure_import_pipeline_schema(isolated_engine)
    finally:
        isolated_engine.dispose()


def downgrade() -> None:
    # Compatibility repair migration: no destructive downgrade.
    return
