"""add place quality scoring columns

models/place.py defines canonical_category, lifecycle_status, quality_tier,
quality_score, completeness_score, photo_score, description_score,
confidence_score, freshness_score and is_spam_poi (plus five CheckConstraints
bounding the score columns), but no migration ever added them. Any ORM query
that selects a Place (e.g. import_pipeline collection COUNT queries) fails
with UndefinedColumn on a database migrated from scratch.

Revision ID: 84665d0fd500
Revises: d4e6f8a0b2c4
Create Date: 2026-07-27 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "84665d0fd500"
down_revision = "d4e6f8a0b2c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("places", sa.Column("canonical_category", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_places_canonical_category"), "places", ["canonical_category"], unique=False)

    op.add_column("places", sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="active"))
    op.create_index(op.f("ix_places_lifecycle_status"), "places", ["lifecycle_status"], unique=False)

    op.add_column("places", sa.Column("quality_tier", sa.String(length=32), nullable=False, server_default="silver"))
    op.create_index(op.f("ix_places_quality_tier"), "places", ["quality_tier"], unique=False)

    op.add_column("places", sa.Column("quality_score", sa.Integer(), nullable=False, server_default="65"))
    op.create_index(op.f("ix_places_quality_score"), "places", ["quality_score"], unique=False)

    op.add_column("places", sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("places", sa.Column("photo_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("places", sa.Column("description_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("places", sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("places", sa.Column("freshness_score", sa.Integer(), nullable=False, server_default="3"))

    op.add_column("places", sa.Column("is_spam_poi", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_places_is_spam_poi"), "places", ["is_spam_poi"], unique=False)

    # batch_alter_table: plain op.create_check_constraint() fails on SQLite
    # ("No support for ALTER of constraints in SQLite dialect") since adding a
    # CHECK constraint requires a table rebuild there; batch mode handles that
    # copy-and-move automatically while emitting a plain ALTER on Postgres.
    with op.batch_alter_table("places") as batch_op:
        batch_op.create_check_constraint("ck_places_quality_score_range", "quality_score >= 0 AND quality_score <= 100")
        batch_op.create_check_constraint("ck_places_completeness_score_range", "completeness_score >= 0 AND completeness_score <= 40")
        batch_op.create_check_constraint("ck_places_photo_score_range", "photo_score >= 0 AND photo_score <= 25")
        batch_op.create_check_constraint("ck_places_description_score_range", "description_score >= 0 AND description_score <= 15")
        batch_op.create_check_constraint("ck_places_confidence_score_range", "confidence_score >= 0 AND confidence_score <= 10")
        batch_op.create_check_constraint("ck_places_freshness_score_range", "freshness_score >= 0 AND freshness_score <= 10")


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_constraint("ck_places_freshness_score_range", type_="check")
        batch_op.drop_constraint("ck_places_confidence_score_range", type_="check")
        batch_op.drop_constraint("ck_places_description_score_range", type_="check")
        batch_op.drop_constraint("ck_places_photo_score_range", type_="check")
        batch_op.drop_constraint("ck_places_quality_score_range", type_="check")

    op.drop_index(op.f("ix_places_is_spam_poi"), table_name="places")
    op.drop_column("places", "is_spam_poi")

    op.drop_column("places", "freshness_score")
    op.drop_column("places", "confidence_score")
    op.drop_column("places", "description_score")
    op.drop_column("places", "photo_score")
    op.drop_column("places", "completeness_score")

    op.drop_index(op.f("ix_places_quality_score"), table_name="places")
    op.drop_column("places", "quality_score")

    op.drop_index(op.f("ix_places_quality_tier"), table_name="places")
    op.drop_column("places", "quality_tier")

    op.drop_index(op.f("ix_places_lifecycle_status"), table_name="places")
    op.drop_column("places", "lifecycle_status")

    op.drop_index(op.f("ix_places_canonical_category"), table_name="places")
    op.drop_column("places", "canonical_category")
