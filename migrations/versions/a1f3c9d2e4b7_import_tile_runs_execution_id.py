"""import_tile_runs: execution_id identity (CITYGO-338)

Tile uniqueness/resume was scoped to (scope_id, tile_id), which let a
brand-new import execution silently reuse an older execution's
checkpoints for the same scope instead of processing every tile fresh,
and mixed diagnostics across executions. This adds an immutable
execution_id column and moves the uniqueness/resume key to
(execution_id, tile_id).

Backfill for existing rows (safe, no history deleted): each pre-existing
row gets execution_id = "job:{city_admin_import_job_id}" when a job id is
present (matching the app's own new execution_id scheme exactly, so a
future retry of that same job continues that row's history), or
"legacy:scope:{scope_id}" when there is no job id. The legacy fallback is
still unique per (execution_id, tile_id): the OLD unique constraint was
(scope_id, tile_id), so no two pre-existing no-job rows for the same
scope ever shared a tile_id — grouping them under one legacy execution id
per scope cannot introduce a duplicate.

Revision ID: a1f3c9d2e4b7
Revises: cc90ca369082
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a1f3c9d2e4b7"
down_revision = "cc90ca369082"
branch_labels = None
depends_on = None

OLD_UNIQUE_NAME = "uq_import_tile_runs_scope_tile"
NEW_UNIQUE_NAME = "uq_import_tile_runs_execution_tile"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("import_tile_runs")}

    if "execution_id" not in columns:
        op.add_column("import_tile_runs", sa.Column("execution_id", sa.String(length=128), nullable=True))

    tile_runs = sa.table(
        "import_tile_runs",
        sa.column("id", sa.Integer()),
        sa.column("execution_id", sa.String(length=128)),
        sa.column("scope_id", sa.Integer()),
        sa.column("city_admin_import_job_id", sa.Integer()),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(tile_runs.c.id, tile_runs.c.scope_id, tile_runs.c.city_admin_import_job_id).where(
            tile_runs.c.execution_id.is_(None)
        )
    ).fetchall()
    for row in rows:
        backfilled = f"job:{row.city_admin_import_job_id}" if row.city_admin_import_job_id is not None else f"legacy:scope:{row.scope_id}"
        connection.execute(
            tile_runs.update().where(tile_runs.c.id == row.id).values(execution_id=backfilled)
        )

    existing_constraints = {c["name"] for c in inspector.get_unique_constraints("import_tile_runs")}
    if OLD_UNIQUE_NAME in existing_constraints:
        with op.batch_alter_table("import_tile_runs") as batch_op:
            batch_op.drop_constraint(OLD_UNIQUE_NAME, type_="unique")

    with op.batch_alter_table("import_tile_runs") as batch_op:
        batch_op.alter_column("execution_id", existing_type=sa.String(length=128), nullable=False)

    existing_constraints = {c["name"] for c in inspector.get_unique_constraints("import_tile_runs")}
    if NEW_UNIQUE_NAME not in existing_constraints:
        with op.batch_alter_table("import_tile_runs") as batch_op:
            batch_op.create_unique_constraint(NEW_UNIQUE_NAME, ["execution_id", "tile_id"])

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("import_tile_runs")}
    if "ix_import_tile_runs_execution_id" not in existing_indexes:
        op.create_index(op.f("ix_import_tile_runs_execution_id"), "import_tile_runs", ["execution_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("import_tile_runs")}
    if "ix_import_tile_runs_execution_id" in existing_indexes:
        op.drop_index(op.f("ix_import_tile_runs_execution_id"), table_name="import_tile_runs")

    existing_constraints = {c["name"] for c in inspector.get_unique_constraints("import_tile_runs")}
    if NEW_UNIQUE_NAME in existing_constraints:
        with op.batch_alter_table("import_tile_runs") as batch_op:
            batch_op.drop_constraint(NEW_UNIQUE_NAME, type_="unique")

    if OLD_UNIQUE_NAME not in existing_constraints:
        with op.batch_alter_table("import_tile_runs") as batch_op:
            batch_op.create_unique_constraint(OLD_UNIQUE_NAME, ["scope_id", "tile_id"])

    columns = {col["name"] for col in inspector.get_columns("import_tile_runs")}
    if "execution_id" in columns:
        with op.batch_alter_table("import_tile_runs") as batch_op:
            batch_op.drop_column("execution_id")
