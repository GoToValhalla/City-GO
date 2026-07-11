from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]
PARENT = "c3d5e7f9a1b3"
REVISION = "d4e6f8a0b2c4"


def _config(db_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", db_url)
    return config


def test_place_source_presence_profile_migration_upgrade_and_downgrade_new(tmp_path):
    db_path = tmp_path / "presence-profile.db"
    db_url = f"sqlite:///{db_path}"
    config = _config(db_url)

    command.upgrade(config, PARENT)
    engine = create_engine(db_url)
    assert "source_profile" not in {column["name"] for column in inspect(engine).get_columns("place_source_presence")}
    engine.dispose()

    command.upgrade(config, REVISION)
    engine = create_engine(db_url)
    assert "source_profile" in {column["name"] for column in inspect(engine).get_columns("place_source_presence")}
    assert "ix_place_source_presence_source_profile" in {
        index["name"] for index in inspect(engine).get_indexes("place_source_presence")
    }
    engine.dispose()

    command.downgrade(config, PARENT)
    engine = create_engine(db_url)
    assert "source_profile" not in {column["name"] for column in inspect(engine).get_columns("place_source_presence")}
    engine.dispose()
