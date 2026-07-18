"""Add bounded lifetime to public user route state registry.

Revision ID: 5a8b0d3f7c2e
Revises: 4f7a9c2e6b1d
"""

from alembic import op
import sqlalchemy as sa

revision = "5a8b0d3f7c2e"
down_revision = "4f7a9c2e6b1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_route_state_registry",
        sa.Column("expires_at", sa.DateTime(), nullable=True),
    )
    bind = op.get_bind()
    expiry_expression = (
        "CURRENT_TIMESTAMP + INTERVAL '1 day'"
        if bind.dialect.name == "postgresql"
        else "datetime(CURRENT_TIMESTAMP, '+1 day')"
    )
    op.execute(
        sa.text(
            "UPDATE user_route_state_registry "
            f"SET expires_at = {expiry_expression} "
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
