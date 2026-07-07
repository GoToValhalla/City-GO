"""Read-only schema snapshot from PostgreSQL information_schema or SQLAlchemy inspector."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def read_alembic_version(engine: Engine) -> str | None:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return None
    with engine.connect() as connection:
        row = connection.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first()
    return str(row[0]) if row else None


def read_schema_snapshot(engine: Engine) -> tuple[set[str], dict[str, set[str]]]:
    if engine.dialect.name == "postgresql":
        return _read_postgres_schema(engine)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    columns = {name: {col["name"] for col in inspector.get_columns(name)} for name in tables}
    return tables, columns


def _read_postgres_schema(engine: Engine) -> tuple[set[str], dict[str, set[str]]]:
    with engine.connect() as connection:
        table_rows = connection.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ).fetchall()
        tables = {str(row[0]) for row in table_rows}
        columns: dict[str, set[str]] = {}
        for table in sorted(tables):
            col_rows = connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = :table_name"
                ),
                {"table_name": table},
            ).fetchall()
            columns[table] = {str(row[0]) for row in col_rows}
    return tables, columns
