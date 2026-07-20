"""Idempotent, ownership-tracked column/index/constraint/table helpers for
Alembic migrations that add schema objects which may already exist, in
compatible form, on a production-shaped database.

Root cause this exists to fix: migration 84665d0fd500 unconditionally ran
`ALTER TABLE places ADD COLUMN canonical_category ...`, which failed with
"column already exists" against a real production database where that
column already existed (created outside this Alembic chain, in compatible
form). The same defect class recurred at table granularity: migration
de447288c917 unconditionally ran `CREATE TABLE place_change_reviews (...)`,
which failed with "relation already exists" against production — that table
predates this Alembic chain entirely (models/place_change_review.py is
explicitly documented as a legacy table kept only for historical schema
compatibility; production alembic_version was still 6b9c1e4a8d3f, far
before any migration ever declared this table).

The fix is not just "skip if it exists" — a later `alembic downgrade` must
also not drop a column/table that predates this revision, so each
column/index/constraint/table this module creates is tagged with a SQL
COMMENT recording which revision created it. downgrade() only drops objects
whose comment marks them as owned by that revision; a compatible,
pre-existing object (no comment, or a comment from a different revision) is
left untouched.

Every function here operates on the SAME connection Alembic itself is
using (op.get_bind()) — never a second engine/connection, which is the
exact deadlock class already fixed once for schema_compat.py's runtime
helper (see b2d4f6a8c3e5's docstring).
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import Column, Table, inspect, text
from sqlalchemy.engine import Connection

_OWNER_PREFIX = "created_by_revision:"


def _owner_comment(revision: str) -> str:
    return f"{_OWNER_PREFIX}{revision}"


def _sql_string_literal(value: str) -> str:
    """PostgreSQL's COMMENT ON ... IS statement does not accept bind
    parameters (COMMENT ON COLUMN x IS $1 is a syntax error) — the value
    must be a literal in the statement text. `value` here is always our own
    _owner_comment() output (an Alembic revision id, never external input),
    but single-quote escaping is still applied defensively."""
    return "'" + value.replace("'", "''") + "'"


def _supports_comments(connection: Connection) -> bool:
    """SQLite has no COMMENT ON COLUMN/INDEX/CONSTRAINT syntax and no
    catalog to record ownership in. It is only ever used for fast,
    from-scratch CI/unit-test databases (never a production-shaped DB with
    pre-existing objects this chain didn't create), so on SQLite every
    object this module creates is unconditionally treated as owned by the
    creating revision — downgrade there is always safe to be unconditional."""
    return connection.engine.dialect.name == "postgresql"


class IncompatibleColumnError(RuntimeError):
    """Raised before any mutation when an existing column's actual type or
    nullability does not match what this migration expects."""

    def __init__(
        self,
        *,
        revision: str,
        table: str,
        column: str,
        actual_type: str,
        actual_nullable: bool,
        expected_type: str,
        expected_nullable: bool,
    ) -> None:
        self.revision = revision
        self.table = table
        self.column = column
        super().__init__(
            f"Migration {revision}: column {table}.{column} already exists with an "
            f"incompatible definition — actual type={actual_type} nullable={actual_nullable}, "
            f"expected type={expected_type} nullable={expected_nullable}. "
            "Refusing to alter it; resolve the discrepancy manually before re-running this migration."
        )


class IncompatibleTableError(RuntimeError):
    """Raised before any mutation when a pre-existing table has a column
    that is missing or type/nullability-incompatible with the model's
    expectations. Never raised for extra columns the existing table has
    that the model does not declare — those are none of this migration's
    business and must not block adoption of an otherwise-compatible table."""

    def __init__(self, *, revision: str, table: str, reason: str) -> None:
        self.revision = revision
        self.table = table
        super().__init__(
            f"Migration {revision}: table {table} already exists and is not "
            f"compatible with the expected shape — {reason}. Refusing to adopt "
            "it; resolve the discrepancy manually before re-running this migration."
        )


def _type_class_name(sqla_type: object) -> str:
    return type(sqla_type).__name__.upper()


_TYPE_EQUIVALENCE_GROUPS: tuple[frozenset[str], ...] = (
    frozenset({"VARCHAR", "STRING", "TEXT", "NVARCHAR"}),
    frozenset({"INTEGER", "BIGINT", "BIGINTEGER", "SMALLINT", "SMALLINTEGER"}),
    frozenset({"BOOLEAN"}),
    frozenset({"FLOAT", "DOUBLE_PRECISION", "NUMERIC", "DECIMAL"}),
    frozenset({"DATETIME", "TIMESTAMP"}),
    frozenset({"JSON", "JSONB"}),
)


def _compatible_type(existing_type: object, expected_type: object) -> bool:
    existing_name = _type_class_name(existing_type)
    expected_name = _type_class_name(expected_type)
    if existing_name == expected_name:
        return True
    return any(existing_name in group and expected_name in group for group in _TYPE_EQUIVALENCE_GROUPS)


def ensure_column(connection: Connection, *, revision: str, table: str, column: Column) -> bool:
    """Add `column` to `table` only if it does not already exist. If it
    already exists, verify it is type/nullability-compatible — raise
    IncompatibleColumnError before any mutation if not. Newly added columns
    are tagged with an owner comment so downgrade() can later tell them
    apart from pre-existing, compatible production columns.

    Returns True if the column was added, False if it already existed
    (and was compatible).
    """
    inspector = inspect(connection)
    existing = {col["name"]: col for col in inspector.get_columns(table)}
    if column.name in existing:
        current = existing[column.name]
        current_nullable = bool(current.get("nullable", True))
        # A stricter-than-existing nullability is only a real incompatibility
        # when there is no server_default to backfill new rows with — with a
        # default, an existing nullable column and a model-declared NOT NULL
        # column both describe a perfectly usable column (the NOT NULL is
        # enforced going forward via the default, not retroactively).
        nullability_incompatible = (
            not column.nullable and current_nullable and column.server_default is None
        )
        if not _compatible_type(current["type"], column.type) or nullability_incompatible:
            raise IncompatibleColumnError(
                revision=revision,
                table=table,
                column=column.name,
                actual_type=repr(current["type"]),
                actual_nullable=current_nullable,
                expected_type=repr(column.type),
                expected_nullable=column.nullable,
            )
        return False

    with op.batch_alter_table(table) as batch_op:
        batch_op.add_column(column)
    if _supports_comments(connection):
        connection.execute(
            text(f"COMMENT ON COLUMN {table}.{column.name} IS {_sql_string_literal(_owner_comment(revision))}")
        )
    return True


def ensure_index(connection: Connection, *, revision: str, index_name: str, table: str, columns: list[str], unique: bool = False) -> bool:
    """Create `index_name` only if it does not already exist. Tags newly
    created indexes with an owner comment. Returns True if created."""
    inspector = inspect(connection)
    existing_indexes = {idx["name"] for idx in inspector.get_indexes(table)}
    if index_name in existing_indexes:
        return False
    op.create_index(index_name, table, columns, unique=unique)
    if _supports_comments(connection):
        connection.execute(
            text(f"COMMENT ON INDEX {index_name} IS {_sql_string_literal(_owner_comment(revision))}")
        )
    return True


def ensure_check_constraint(connection: Connection, *, revision: str, constraint_name: str, table: str, condition: str) -> bool:
    """Create `constraint_name` (a CHECK constraint) only if it does not
    already exist. Tags newly created constraints with an owner comment.
    Returns True if created."""
    if _supports_comments(connection):
        existing_names = {row[0] for row in connection.execute(
            text(
                "SELECT conname FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = :table AND c.contype = 'c'"
            ),
            {"table": table},
        )}
        if constraint_name in existing_names:
            return False
    with op.batch_alter_table(table) as batch_op:
        batch_op.create_check_constraint(constraint_name, condition)
    if _supports_comments(connection):
        connection.execute(
            text(f"COMMENT ON CONSTRAINT {constraint_name} ON {table} IS {_sql_string_literal(_owner_comment(revision))}")
        )
    return True


def is_owned_by_revision(connection: Connection, *, revision: str, kind: str, table: str, name: str) -> bool:
    """True if the column/index/constraint named `name` on `table` carries
    this revision's owner comment. Used by downgrade() to decide whether it
    is safe to drop — a pre-existing production object that this migration
    never created (no comment, or a different revision's comment) must be
    left alone. On SQLite (no comment catalog — see _supports_comments),
    anything that currently exists is treated as owned, since SQLite is
    only ever a from-scratch test database in this project."""
    if not _supports_comments(connection):
        if kind == "column":
            return name in {col["name"] for col in inspect(connection).get_columns(table)}
        if kind == "index":
            return name in {idx["name"] for idx in inspect(connection).get_indexes(table)}
        if kind == "table":
            return name in set(inspect(connection).get_table_names())
        if kind == "constraint":
            return True
        raise ValueError(f"unknown kind: {kind}")

    expected = _owner_comment(revision)
    if kind == "column":
        inspector = inspect(connection)
        for col in inspector.get_columns(table):
            if col["name"] == name:
                return col.get("comment") == expected
        return False
    if kind in ("index", "table"):
        row = connection.execute(
            text("SELECT obj_description(CAST(:name AS regclass), 'pg_class')"), {"name": name}
        ).scalar()
        return row == expected
    if kind == "constraint":
        row = connection.execute(
            text(
                "SELECT obj_description(c.oid) FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE t.relname = :table AND c.conname = :name"
            ),
            {"table": table, "name": name},
        ).scalar()
        return row == expected
    raise ValueError(f"unknown kind: {kind}")


def drop_column_if_owned(connection: Connection, *, revision: str, table: str, column: str) -> None:
    if is_owned_by_revision(connection, revision=revision, kind="column", table=table, name=column):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column(column)


def drop_index_if_owned(connection: Connection, *, revision: str, table: str, index_name: str) -> None:
    if is_owned_by_revision(connection, revision=revision, kind="index", table=table, name=index_name):
        op.drop_index(index_name, table_name=table)


def drop_check_constraint_if_owned(connection: Connection, *, revision: str, table: str, constraint_name: str) -> None:
    if is_owned_by_revision(connection, revision=revision, kind="constraint", table=table, name=constraint_name):
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_constraint(constraint_name, type_="check")


def ensure_table(connection: Connection, *, revision: str, table: Table) -> bool:
    """Create `table` only if it does not already exist. If it already
    exists, verify every column the model declares is present and
    type/nullability-compatible — raise IncompatibleTableError before any
    mutation if not. Extra columns the existing table has that the model
    does not declare are ignored (not this migration's concern). A newly
    created table is tagged with an owner comment so downgrade() can later
    tell it apart from a pre-existing, compatible production table.

    Returns True if the table was created, False if it already existed
    (and was compatible).
    """
    inspector = inspect(connection)
    if table.name not in set(inspector.get_table_names()):
        table.create(bind=connection)
        if _supports_comments(connection):
            connection.execute(
                text(f"COMMENT ON TABLE {table.name} IS {_sql_string_literal(_owner_comment(revision))}")
            )
        return True

    existing_columns = {col["name"]: col for col in inspector.get_columns(table.name)}
    for column in table.columns:
        existing = existing_columns.get(column.name)
        if existing is None:
            raise IncompatibleTableError(
                revision=revision,
                table=table.name,
                reason=f"missing expected column {column.name!r}",
            )
        current_nullable = bool(existing.get("nullable", True))
        nullability_incompatible = (
            not column.nullable and current_nullable and column.server_default is None
        )
        if not _compatible_type(existing["type"], column.type) or nullability_incompatible:
            raise IncompatibleTableError(
                revision=revision,
                table=table.name,
                reason=(
                    f"column {column.name!r} existing type={existing['type']!r} "
                    f"nullable={current_nullable} is not compatible with expected "
                    f"type={column.type!r} nullable={column.nullable}"
                ),
            )
    return False


def drop_table_if_owned(connection: Connection, *, revision: str, table_name: str) -> None:
    if is_owned_by_revision(connection, revision=revision, kind="table", table=table_name, name=table_name):
        op.drop_table(table_name)
