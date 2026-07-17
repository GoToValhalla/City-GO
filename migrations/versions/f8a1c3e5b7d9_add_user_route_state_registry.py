"""Add authoritative registry for current public user route state.

Revision ID: f8a1c3e5b7d9
Revises: e7f9b2c4a6d8
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f8a1c3e5b7d9"
down_revision = "e7f9b2c4a6d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_route_state_registry",
        sa.Column("route_id", sa.String(length=255), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("place_ids", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.PrimaryKeyConstraint("route_id"),
    )
    op.create_index("ix_user_route_state_registry_city_id", "user_route_state_registry", ["city_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_route_state_registry_city_id", table_name="user_route_state_registry")
    op.drop_table("user_route_state_registry")
