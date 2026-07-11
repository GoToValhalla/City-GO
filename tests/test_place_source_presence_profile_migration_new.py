import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]
PARENT = "c3d5e7f9a1b3"
REVISION = "d4e6f8a0b2c4"


def _config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def _create_legacy_presence_table(db_url: str) -> None:
    """Model the real pre-migration state: runtime-created table without source_profile."""
    engine = create_engine(db_url)
    metadata = MetaData()
    Table(
        "place_source_presence",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_external_id", String(128), nullable=False),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_place_source_presence_profile_migration_upgrade_and_downgrade_new(tmp_path):
    db_path = tmp_path / "presence-profile.db"
    db_url = f"sqlite:///{db_path}"
    previous_database_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = db_url
    try:
        config = _config(db_url)

        command.upgrade(config, PARENT)
        _create_legacy_presence_table(db_url)

        engine = create_engine(db_url)
        assert "source_profile" not in {
            column["name"] for column in inspect(engine).get_columns("place_source_presence")
        }
        engine.dispose()

        command.upgrade(config, REVISION)
        engine = create_engine(db_url)
        assert "source_profile" in {
            column["name"] for column in inspect(engine).get_columns("place_source_presence")
        }
        assert "ix_place_source_presence_source_profile" in {
            index["name"] for index in inspect(engine).get_indexes("place_source_presence")
        }
        engine.dispose()

        command.downgrade(config, PARENT)
        engine = create_engine(db_url)
        assert "source_profile" not in {
            column["name"] for column in inspect(engine).get_columns("place_source_presence")
        }
        engine.dispose()
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
