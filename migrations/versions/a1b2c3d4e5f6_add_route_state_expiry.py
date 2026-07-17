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
        sa.Column(
            "expires_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP + INTERVAL '1 day')"),
        ),
    )
    op.create_index(
        "ix_user_route_state_registry_expires_at",
        "user_route_state_registry",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_route_state_registry_expires_at", table_name="user_route_state_registry")
    op.drop_column("user_route_state_registry", "expires_at")
