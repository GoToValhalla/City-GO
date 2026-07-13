"""add place dedup and geo precision columns

models/place.py also defines is_duplicate_suspected, geo_precision and
critical_field_expired, which — like the columns added in 84665d0fd500 —
were never migrated. Discovered when GET /admin/import-jobs/{city_id}
(build_import_job_payload -> db.query(Place).filter(...).count()) failed
with UndefinedColumn on a database migrated from scratch.

Revision ID: f0c0c48aa12a
Revises: 84665d0fd500
Create Date: 2026-07-27 01:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "f0c0c48aa12a"
down_revision = "84665d0fd500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("places", sa.Column("is_duplicate_suspected", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_places_is_duplicate_suspected"), "places", ["is_duplicate_suspected"], unique=False)

    op.add_column("places", sa.Column("geo_precision", sa.String(length=32), nullable=True))
    op.create_index(op.f("ix_places_geo_precision"), "places", ["geo_precision"], unique=False)

    op.add_column("places", sa.Column("critical_field_expired", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_index(op.f("ix_places_critical_field_expired"), "places", ["critical_field_expired"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_places_critical_field_expired"), table_name="places")
    op.drop_column("places", "critical_field_expired")

    op.drop_index(op.f("ix_places_geo_precision"), table_name="places")
    op.drop_column("places", "geo_precision")

    op.drop_index(op.f("ix_places_is_duplicate_suspected"), table_name="places")
    op.drop_column("places", "is_duplicate_suspected")
