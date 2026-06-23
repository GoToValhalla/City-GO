from sqlalchemy import create_engine, text

from scripts.repair_alembic_overlapping_heads import (
    CURRENT_DESCENDANT_REVISION,
    LEGACY_ANCESTOR_REVISION,
    repair_overlapping_heads,
)


def _engine_with_revisions(*revisions: str):
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        for revision in revisions:
            connection.execute(
                text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
                {"revision": revision},
            )
    return engine


def _revisions(engine) -> set[str]:
    with engine.connect() as connection:
        return set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())


def test_repair_removes_only_redundant_ancestor_new() -> None:
    engine = _engine_with_revisions(LEGACY_ANCESTOR_REVISION, CURRENT_DESCENDANT_REVISION)

    assert repair_overlapping_heads(engine) is True
    assert _revisions(engine) == {CURRENT_DESCENDANT_REVISION}


def test_repair_is_idempotent_for_current_head_new() -> None:
    engine = _engine_with_revisions(CURRENT_DESCENDANT_REVISION)

    assert repair_overlapping_heads(engine) is False
    assert _revisions(engine) == {CURRENT_DESCENDANT_REVISION}


def test_repair_does_nothing_before_version_table_exists_new() -> None:
    engine = create_engine("sqlite://")

    assert repair_overlapping_heads(engine) is False
