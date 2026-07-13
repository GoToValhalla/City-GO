"""add missing source_observations provenance columns

This used to delegate to services.import_pipeline.schema_compat's
ensure_import_pipeline_schema(op.get_bind().engine) — passing the Engine
looked safe (same engine Alembic itself uses), but ensure_import_pipeline_schema
always calls engine.connect() internally, which pulls a brand-new pooled
connection rather than reusing Alembic's own open connection/transaction.
Under a production-shaped DB where source_observations already exists but
is missing these columns (verified locally: downgrade to d0e1f2a3b4c5, then
upgrade head — hangs deterministically without this fix), that second
connection blocks forever on a lock Alembic's own still-open transaction
holds from an earlier migration in the same run. Doing the DDL directly
here, on Alembic's actual bound connection (op.get_bind()), removes the
second connection entirely.

Revision ID: b2d4f6a8c3e5
Revises: a1c2d3e4f5b6
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b2d4f6a8c3e5"
down_revision = "a1c2d3e4f5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("source_observations")}

    with op.batch_alter_table("source_observations") as batch_op:
        if "source_license" not in existing_columns:
            batch_op.add_column(sa.Column("source_license", sa.String(length=255), nullable=True))
        if "attribution_text" not in existing_columns:
            batch_op.add_column(sa.Column("attribution_text", sa.String(length=1000), nullable=True))
        if "idempotency_key" not in existing_columns:
            batch_op.add_column(sa.Column("idempotency_key", sa.String(length=255), nullable=True))

    existing_indexes = {index["name"] for index in inspector.get_indexes("source_observations")}
    existing_unique_constraints = {
        constraint["name"] for constraint in inspector.get_unique_constraints("source_observations")
    }
    if "ix_source_observations_source_license" not in existing_indexes:
        op.create_index("ix_source_observations_source_license", "source_observations", ["source_license"])
    if "ix_source_observations_idempotency_key" not in existing_indexes:
        op.create_index("ix_source_observations_idempotency_key", "source_observations", ["idempotency_key"])
    if (
        "uq_source_observation_idempotency_key" not in existing_unique_constraints
        and "uq_source_observation_idempotency_key" not in existing_indexes
    ):
        # Unique index instead of a named UNIQUE constraint — equivalent
        # enforcement, and matches the runtime shim this migration replaces
        # (which also used CREATE UNIQUE INDEX, not ADD CONSTRAINT).
        op.create_index(
            "uq_source_observation_idempotency_key", "source_observations", ["idempotency_key"], unique=True
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("source_observations")}
    if "uq_source_observation_idempotency_key" in existing_indexes:
        op.drop_index("uq_source_observation_idempotency_key", table_name="source_observations")
    if "ix_source_observations_idempotency_key" in existing_indexes:
        op.drop_index("ix_source_observations_idempotency_key", table_name="source_observations")
    if "ix_source_observations_source_license" in existing_indexes:
        op.drop_index("ix_source_observations_source_license", table_name="source_observations")

    existing_columns = {column["name"] for column in inspector.get_columns("source_observations")}
    with op.batch_alter_table("source_observations") as batch_op:
        if "idempotency_key" in existing_columns:
            batch_op.drop_column("idempotency_key")
        if "attribution_text" in existing_columns:
            batch_op.drop_column("attribution_text")
        if "source_license" in existing_columns:
            batch_op.drop_column("source_license")
