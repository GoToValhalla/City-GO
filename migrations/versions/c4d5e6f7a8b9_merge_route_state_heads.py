"""Merge route-state registry and cleanup-index migration heads.

Revision ID: c4d5e6f7a8b9
Revises: a1b2c3d4e5f6, b3c4d5e6f7a8

The cleanup-index migration was reattached from a1b2c3d4e5f6 to the
then-current import-job head e7f9b2c4a6d8. That preserved the import chain
but left a1b2c3d4e5f6 as a second Alembic head. This no-op merge revision
rejoins both already-valid branches without rewriting migration history.
"""

revision = "c4d5e6f7a8b9"
down_revision = ("a1b2c3d4e5f6", "b3c4d5e6f7a8")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
