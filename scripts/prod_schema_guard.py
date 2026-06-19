from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateColumn

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.base import Base
from db.session import engine


MODEL_PACKAGE = "models"


# Production emergency guard.
# Alembic currently reports OK while production schema is still behind application models.
# This guard is intentionally broad: it imports all model modules, creates missing tables,
# and adds missing columns before backend restart so prod does not stay broken.
def main() -> None:
    _import_all_models()
    created_tables = _create_missing_tables(engine)
    added_columns = _add_missing_columns(engine)
    print({"created_tables": created_tables, "added_columns": added_columns})


def _import_all_models() -> None:
    package = importlib.import_module(MODEL_PACKAGE)
    package_path = getattr(package, "__path__", None)
    if package_path is None:
        return
    for module_info in pkgutil.iter_modules(package_path):
        if module_info.name.startswith("_"):
            continue
        importlib.import_module(f"{MODEL_PACKAGE}.{module_info.name}")


def _create_missing_tables(db_engine: Engine) -> list[str]:
    inspector = inspect(db_engine)
    existing_tables = set(inspector.get_table_names())
    missing_tables = [table for table in Base.metadata.sorted_tables if table.name not in existing_tables]
    for table in missing_tables:
        table.create(bind=db_engine, checkfirst=True)
    return [table.name for table in missing_tables]


def _add_missing_columns(db_engine: Engine) -> list[str]:
    inspector = inspect(db_engine)
    existing_tables = set(inspector.get_table_names())
    added: list[str] = []
    with db_engine.begin() as connection:
        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing_columns:
                    continue
                column_sql = _compile_column_for_add(db_engine, column)
                connection.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN {column_sql}'))
                added.append(f"{table.name}.{column.name}")
    return added


def _compile_column_for_add(db_engine: Engine, column) -> str:
    # PostgreSQL cannot add a new NOT NULL column without values into non-empty tables.
    # For emergency compatibility, add missing model columns as nullable first. The app
    # already treats these operational fields defensively, and proper constraints can be
    # restored later via explicit Alembic migrations.
    copied = column.copy()
    copied.nullable = True
    copied.primary_key = False
    copied.unique = False
    return str(CreateColumn(copied).compile(dialect=db_engine.dialect))


if __name__ == "__main__":
    main()
