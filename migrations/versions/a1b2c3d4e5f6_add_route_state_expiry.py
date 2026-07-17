"""Add bounded lifetime to public user route state registry.

Revision ID: a1b2c3d4e5f6
Revises: f8a1c3e5b7d9
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "f8a1c3e5b7d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_route_state_registry",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE user_route_state_registry "
            "SET expires_at = CURRENT_TIMESTAMP "
            "WHERE expires_at IS NULL"
        )
    )
    with op.batch_alter_table("user_route_state_registry") as batch:
        batch.alter_column("expires_at", existing_type=sa.DateTime(), nullable=False)
        batch.create_index("ix_user_route_state_registry_expires_at", ["expires_at"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("user_route_state_registry") as batch:
        batch.drop_index("ix_user_route_state_registry_expires_at")
        batch.drop_column("expires_at")
