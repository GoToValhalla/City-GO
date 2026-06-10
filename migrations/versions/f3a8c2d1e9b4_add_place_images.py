"""add_place_images

Revision ID: f3a8c2d1e9b4
Revises: 2b7f6a4d9c10
Create Date: 2026-05-20 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a8c2d1e9b4"
down_revision: Union[str, None] = "2b7f6a4d9c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "place_images",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=2000), nullable=False),
        sa.Column("thumbnail_url", sa.String(length=2000), nullable=True),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=True),
        sa.Column("attribution", sa.String(length=1000), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="needs_review"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("reviewed_by", sa.String(length=255), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("review_comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_images_id", "place_images", ["id"], unique=False)
    op.create_index("ix_place_images_place_id", "place_images", ["place_id"], unique=False)
    op.create_index("ix_place_images_source_type", "place_images", ["source_type"], unique=False)
    op.create_index("ix_place_images_status", "place_images", ["status"], unique=False)
    op.create_index("ix_place_images_is_primary", "place_images", ["is_primary"], unique=False)
    op.create_index(
        "ix_place_images_place_id_image_url",
        "place_images",
        ["place_id", "image_url"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_place_images_place_id_image_url", table_name="place_images")
    op.drop_index("ix_place_images_is_primary", table_name="place_images")
    op.drop_index("ix_place_images_status", table_name="place_images")
    op.drop_index("ix_place_images_source_type", table_name="place_images")
    op.drop_index("ix_place_images_place_id", table_name="place_images")
    op.drop_index("ix_place_images_id", table_name="place_images")
    op.drop_table("place_images")
