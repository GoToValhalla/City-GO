"""add place quality scoring columns

models/place.py defines canonical_category, lifecycle_status, quality_tier,
quality_score, completeness_score, photo_score, description_score,
confidence_score, freshness_score and is_spam_poi (plus five CheckConstraints
bounding the score columns), but no migration ever added them. Any ORM query
that selects a Place (e.g. import_pipeline collection COUNT queries) fails
with UndefinedColumn on a database migrated from scratch.

Idempotent/ownership-safe (services.migration_column_guard): a real
production deploy (e150f85) failed here with
"column canonical_category of relation places already exists" — that
column had been created outside this Alembic chain, in compatible form,
on a production-shaped database. Every add_column/create_index/
create_check_constraint below now checks first via
services.migration_column_guard.ensure_*, using op.get_bind() (Alembic's
own connection — never a second one), and tags anything it actually
creates with a SQL COMMENT recording this revision, so downgrade() can
later tell newly-created objects apart from pre-existing, compatible
production columns and never drops the latter.

Revision ID: 84665d0fd500
Revises: d4e6f8a0b2c4
Create Date: 2026-07-27 01:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

from services.migration_column_guard import (
    drop_check_constraint_if_owned,
    drop_column_if_owned,
    drop_index_if_owned,
    ensure_check_constraint,
    ensure_column,
    ensure_index,
)

revision = "84665d0fd500"
down_revision = "d4e6f8a0b2c4"
branch_labels = None
depends_on = None

_TABLE = "places"


def upgrade() -> None:
    bind = op.get_bind()

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("canonical_category", sa.String(length=100), nullable=True))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_canonical_category"), table=_TABLE, columns=["canonical_category"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("lifecycle_status", sa.String(length=32), nullable=False, server_default="active"))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_lifecycle_status"), table=_TABLE, columns=["lifecycle_status"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("quality_tier", sa.String(length=32), nullable=False, server_default="silver"))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_quality_tier"), table=_TABLE, columns=["quality_tier"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("quality_score", sa.Integer(), nullable=False, server_default="65"))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_quality_score"), table=_TABLE, columns=["quality_score"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("completeness_score", sa.Integer(), nullable=False, server_default="0"))
    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("photo_score", sa.Integer(), nullable=False, server_default="0"))
    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("description_score", sa.Integer(), nullable=False, server_default="0"))
    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("confidence_score", sa.Integer(), nullable=False, server_default="0"))
    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("freshness_score", sa.Integer(), nullable=False, server_default="3"))

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("is_spam_poi", sa.Boolean(), nullable=False, server_default=sa.false()))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_is_spam_poi"), table=_TABLE, columns=["is_spam_poi"])

    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_quality_score_range", table=_TABLE, condition="quality_score >= 0 AND quality_score <= 100")
    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_completeness_score_range", table=_TABLE, condition="completeness_score >= 0 AND completeness_score <= 40")
    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_photo_score_range", table=_TABLE, condition="photo_score >= 0 AND photo_score <= 25")
    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_description_score_range", table=_TABLE, condition="description_score >= 0 AND description_score <= 15")
    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_confidence_score_range", table=_TABLE, condition="confidence_score >= 0 AND confidence_score <= 10")
    ensure_check_constraint(bind, revision=revision, constraint_name="ck_places_freshness_score_range", table=_TABLE, condition="freshness_score >= 0 AND freshness_score <= 10")


def downgrade() -> None:
    bind = op.get_bind()

    drop_check_constraint_if_owned(bind, revision=revision, table=_TABLE, constraint_name="ck_places_freshness_score_range")
    drop_check_constraint_if_owned(bind, revision=revision, table=_TABLE, constraint_name="ck_places_confidence_score_range")
    drop_check_constraint_if_owned(bind, revision=revision, table=_TABLE, constraint_name="ck_places_description_score_range")
    drop_check_constraint_if_owned(bind, revision=revision, table=_TABLE, constraint_name="ck_places_photo_score_range")
    drop_check_constraint_if_owned(bind, revision=revision, table=_TABLE, constraint_name="ck_places_quality_score_range")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_is_spam_poi"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="is_spam_poi")

    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="freshness_score")
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="confidence_score")
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="description_score")
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="photo_score")
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="completeness_score")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_quality_score"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="quality_score")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_quality_tier"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="quality_tier")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_lifecycle_status"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="lifecycle_status")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_canonical_category"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="canonical_category")
