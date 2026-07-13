"""import schema compatibility for OSM collecting_places

Revision ID: a1c2d3e4f5b6
Revises: c9d0e1f2a3b4
"""

from __future__ import annotations

revision = "a1c2d3e4f5b6"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ensure_import_pipeline_schema() used to run here via a SECOND, isolated
    # DB connection (create_engine(op.get_bind().engine.url)). That is the
    # exact deadlock class already fixed once for place_field_provenance
    # (migration b536b3b1ab93): a second connection contending for locks on
    # tables Alembic's own still-open migration transaction had already
    # touched earlier in the same upgrade run — reproducibly hangs when this
    # migration is (re)run against a production-shaped DB where
    # source_observations already exists but is missing these columns (audit
    # fixture: city_guide_prod_shaped_fixture, downgrade to d0e1f2a3b4c5 then
    # upgrade head — hangs deterministically without this fix).
    #
    # migration b2d4f6a8c3e5 (revises this one) already performs the exact
    # same schema repair via op.get_bind().engine directly — the same
    # connection/transaction Alembic itself uses, so no second connection and
    # no deadlock. This migration's own call was therefore both unsafe and
    # fully redundant; removed rather than duplicated.
    return


def downgrade() -> None:
    # Compatibility repair migration: no destructive downgrade.
    return
