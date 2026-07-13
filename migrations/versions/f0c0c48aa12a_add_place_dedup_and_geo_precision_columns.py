"""add place dedup and geo precision columns

models/place.py also defines is_duplicate_suspected, geo_precision and
critical_field_expired, which — like the columns added in 84665d0fd500 —
were never migrated. Discovered when GET /admin/import-jobs/{city_id}
(build_import_job_payload -> db.query(Place).filter(...).count()) failed
with UndefinedColumn on a database migrated from scratch.

Idempotent/ownership-safe (services.migration_column_guard) for the same
reason as 84665d0fd500: a production-shaped database may already have any
subset of these columns in compatible form, created outside this Alembic
chain. See that migration's docstring for the full explanation.

Revision ID: f0c0c48aa12a
Revises: 84665d0fd500
Create Date: 2026-07-27 01:15:00.000000
"""

from alembic import op
import sqlalchemy as sa

from services.migration_column_guard import (
    drop_column_if_owned,
    drop_index_if_owned,
    ensure_column,
    ensure_index,
)

revision = "f0c0c48aa12a"
down_revision = "84665d0fd500"
branch_labels = None
depends_on = None

_TABLE = "places"


def upgrade() -> None:
    bind = op.get_bind()

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("is_duplicate_suspected", sa.Boolean(), nullable=False, server_default=sa.false()))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_is_duplicate_suspected"), table=_TABLE, columns=["is_duplicate_suspected"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("geo_precision", sa.String(length=32), nullable=True))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_geo_precision"), table=_TABLE, columns=["geo_precision"])

    ensure_column(bind, revision=revision, table=_TABLE, column=sa.Column("critical_field_expired", sa.Boolean(), nullable=False, server_default=sa.false()))
    ensure_index(bind, revision=revision, index_name=op.f("ix_places_critical_field_expired"), table=_TABLE, columns=["critical_field_expired"])


def downgrade() -> None:
    bind = op.get_bind()

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_critical_field_expired"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="critical_field_expired")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_geo_precision"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="geo_precision")

    drop_index_if_owned(bind, revision=revision, table=_TABLE, index_name=op.f("ix_places_is_duplicate_suspected"))
    drop_column_if_owned(bind, revision=revision, table=_TABLE, column="is_duplicate_suspected")
