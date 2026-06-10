"""add_place_existence_confidence

Revision ID: 5f2d7a91c4b8
Revises: f3a8c2d1e9b4, b9d2c1f0a882
Create Date: 2026-06-05 23:55:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5f2d7a91c4b8"
down_revision: Union[str, tuple[str, str], None] = ("f3a8c2d1e9b4", "b9d2c1f0a882")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("existence_confidence_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("places", sa.Column("existence_confidence_level", sa.String(length=32), nullable=False, server_default="unknown"))
    op.add_column("places", sa.Column("verification_status", sa.String(length=32), nullable=False, server_default="unverified"))
    op.add_column("places", sa.Column("verification_source", sa.String(length=64), nullable=True))
    op.add_column("places", sa.Column("verification_method", sa.String(length=64), nullable=True))
    op.add_column("places", sa.Column("verified_at", sa.DateTime(), nullable=True))
    op.add_column("places", sa.Column("verified_by", sa.String(length=255), nullable=True))
    op.add_column("places", sa.Column("needs_recheck_at", sa.DateTime(), nullable=True))
    op.add_column("places", sa.Column("verification_comment", sa.String(length=1000), nullable=True))

    op.create_index("ix_places_existence_confidence_score", "places", ["existence_confidence_score"])
    op.create_index("ix_places_existence_confidence_level", "places", ["existence_confidence_level"])
    op.create_index("ix_places_verification_status", "places", ["verification_status"])

    op.create_table(
        "place_verifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("confidence_score_before", sa.Integer(), nullable=True),
        sa.Column("confidence_score_after", sa.Integer(), nullable=True),
        sa.Column("confidence_level_before", sa.String(length=32), nullable=True),
        sa.Column("confidence_level_after", sa.String(length=32), nullable=True),
        sa.Column("verification_source", sa.String(length=64), nullable=True),
        sa.Column("verification_method", sa.String(length=64), nullable=True),
        sa.Column("verifier", sa.String(length=255), nullable=True),
        sa.Column("verifier_lat", sa.Float(), nullable=True),
        sa.Column("verifier_lng", sa.Float(), nullable=True),
        sa.Column("distance_to_place_meters", sa.Float(), nullable=True),
        sa.Column("photo_url", sa.String(length=2000), nullable=True),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_place_verifications_id", "place_verifications", ["id"])
    op.create_index("ix_place_verifications_place_id", "place_verifications", ["place_id"])
    op.create_index("ix_place_verifications_status", "place_verifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_place_verifications_status", table_name="place_verifications")
    op.drop_index("ix_place_verifications_place_id", table_name="place_verifications")
    op.drop_index("ix_place_verifications_id", table_name="place_verifications")
    op.drop_table("place_verifications")

    op.drop_index("ix_places_verification_status", table_name="places")
    op.drop_index("ix_places_existence_confidence_level", table_name="places")
    op.drop_index("ix_places_existence_confidence_score", table_name="places")

    op.drop_column("places", "verification_comment")
    op.drop_column("places", "needs_recheck_at")
    op.drop_column("places", "verified_by")
    op.drop_column("places", "verified_at")
    op.drop_column("places", "verification_method")
    op.drop_column("places", "verification_source")
    op.drop_column("places", "verification_status")
    op.drop_column("places", "existence_confidence_level")
    op.drop_column("places", "existence_confidence_score")
