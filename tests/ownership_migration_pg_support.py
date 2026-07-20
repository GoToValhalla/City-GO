from __future__ import annotations

import os
import subprocess

from sqlalchemy import create_engine, text

DB_NAME = "city_go_ownership_migration_pytest"
DB_URL = f"postgresql+psycopg://user@localhost:5432/{DB_NAME}"
PREDECESSOR = "de447288c917"
HEAD = "b7e4f1a9082c"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": DB_URL}
    return subprocess.run(args, check=check, text=True, capture_output=True, env=env)


def recreate_database() -> None:
    run("dropdb", "--if-exists", "--force", DB_NAME)
    run("createdb", DB_NAME)


def drop_database() -> None:
    run("dropdb", "--if-exists", "--force", DB_NAME)


def alembic(target: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = "downgrade" if target == "downgrade" else "upgrade"
    revision = PREDECESSOR if target == "downgrade" else target
    return run(".venv/bin/alembic", command, revision, check=check)


def execute(statement: str) -> None:
    engine = create_engine(DB_URL)
    try:
        with engine.begin() as connection:
            connection.execute(text(statement))
    finally:
        engine.dispose()


def scalar(statement: str) -> object:
    engine = create_engine(DB_URL)
    try:
        with engine.connect() as connection:
            return connection.execute(text(statement)).scalar()
    finally:
        engine.dispose()
