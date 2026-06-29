"""place route layers

Revision ID: c8d4e6f9a102
Revises: b7c2d4e6f8a0
"""

from alembic import op
import sqlalchemy as sa

revision = "c8d4e6f9a102"
down_revision = "b7c2d4e6f8a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("places", sa.Column("place_layer", sa.String(64), nullable=False, server_default="tourist_catalog"))
    op.add_column("places", sa.Column("route_policy", sa.String(64), nullable=False, server_default="city_walking"))
    op.add_column("places", sa.Column("tourist_eligible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("places", sa.Column("transport_required", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column("places", "transport_required")
    op.drop_column("places", "tourist_eligible")
    op.drop_column("places", "route_policy")
    op.drop_column("places", "place_layer")
