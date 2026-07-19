from __future__ import annotations

import importlib.util
from contextlib import contextmanager
from pathlib import Path

import pytest

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "4f7a9c2d1e6b_defer_publication_reason_constraint.py"
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("publication_constraint_compensation", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_drops_existing_constraint(monkeypatch) -> None:
    migration = _load_migration()
    calls: list[tuple[str, str]] = []

    class Batch:
        def drop_constraint(self, name: str, *, type_: str) -> None:
            calls.append((name, type_))

    @contextmanager
    def batch_alter_table(table_name: str):
        assert table_name == "places"
        yield Batch()

    monkeypatch.setattr(migration, "_constraint_exists", lambda: True)
    monkeypatch.setattr(migration.op, "batch_alter_table", batch_alter_table)
    migration.upgrade()
    assert calls == [("ck_places_publication_reason_consistency", "check")]


def test_upgrade_is_noop_when_constraint_absent(monkeypatch) -> None:
    migration = _load_migration()
    called = False

    @contextmanager
    def batch_alter_table(_table_name: str):
        nonlocal called
        called = True
        yield object()

    monkeypatch.setattr(migration, "_constraint_exists", lambda: False)
    monkeypatch.setattr(migration.op, "batch_alter_table", batch_alter_table)
    migration.upgrade()
    assert called is False


def test_downgrade_restores_constraint_after_clean_preflight(monkeypatch) -> None:
    migration = _load_migration()
    calls: list[tuple[str, str]] = []

    class Batch:
        def create_check_constraint(self, name: str, sql: str) -> None:
            calls.append((name, sql))

    @contextmanager
    def batch_alter_table(table_name: str):
        assert table_name == "places"
        yield Batch()

    monkeypatch.setattr(migration, "_constraint_exists", lambda: False)
    monkeypatch.setattr(migration, "_inconsistent_count", lambda: 0)
    monkeypatch.setattr(migration.op, "batch_alter_table", batch_alter_table)
    migration.downgrade()
    assert calls == [(migration.CONSTRAINT_NAME, migration.CONSTRAINT_SQL)]


def test_downgrade_fails_closed_on_inconsistent_data(monkeypatch) -> None:
    migration = _load_migration()
    monkeypatch.setattr(migration, "_constraint_exists", lambda: False)
    monkeypatch.setattr(migration, "_inconsistent_count", lambda: 3)
    with pytest.raises(RuntimeError, match="3 inconsistent places"):
        migration.downgrade()
