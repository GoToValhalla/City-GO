"""Align the route-state registry index with bounded cleanup ordering.

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
"""

from alembic import op

revision = "b3c4d5e6f7a8"
down_revision = "a1b2c3d4e5f6"
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
