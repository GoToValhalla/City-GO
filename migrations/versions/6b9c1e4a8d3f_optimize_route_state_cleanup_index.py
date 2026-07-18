"""Align the route-state registry index with bounded cleanup ordering.

Revision ID: 6b9c1e4a8d3f
Revises: 5a8b0d3f7c2e
"""

from alembic import op

revision = "6b9c1e4a8d3f"
down_revision = "5a8b0d3f7c2e"
branch_labels = None
depends_on = None

_OLD_INDEX = "ix_user_route_state_registry_expires_at"
_CLEANUP_INDEX = "ix_user_route_state_registry_expires_at_route_id"


def upgrade() -> None:
    with op.batch_alter_table("user_route_state_registry") as batch:
        batch.drop_index(_OLD_INDEX)
        batch.create_index(
            _CLEANUP_INDEX,
            ["expires_at", "route_id"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("user_route_state_registry") as batch:
        batch.drop_index(_CLEANUP_INDEX)
        batch.create_index(
            _OLD_INDEX,
            ["expires_at"],
            unique=False,
        )
