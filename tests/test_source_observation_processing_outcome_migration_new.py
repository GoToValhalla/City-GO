"""Upgrade/downgrade contract for the processing_outcome column migration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[1]
REVISION = "c3d5e7f9a1b3"
PARENT_REVISION = "f1a2b3c4d5e7"


def _alembic_config(database_url: str) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def test_migration_adds_and_removes_processing_outcome_column_new() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "migration_check.db"
        database_url = f"sqlite:///{db_path}"
        prev = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = database_url
        try:
            cfg = _alembic_config(database_url)
            command.upgrade(cfg, PARENT_REVISION)

            engine = create_engine(database_url)
            columns_before = {c["name"] for c in inspect(engine).get_columns("source_observations")}
            assert "processing_outcome" not in columns_before
            engine.dispose()

            command.upgrade(cfg, REVISION)

            engine = create_engine(database_url)
            columns_after = {c["name"] for c in inspect(engine).get_columns("source_observations")}
            assert "processing_outcome" in columns_after
            engine.dispose()

            command.downgrade(cfg, PARENT_REVISION)

            engine = create_engine(database_url)
            columns_downgraded = {c["name"] for c in inspect(engine).get_columns("source_observations")}
            assert "processing_outcome" not in columns_downgraded
            engine.dispose()
        finally:
            if prev is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = prev
