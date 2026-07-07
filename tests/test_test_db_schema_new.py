"""Проверка: alembic-миграции создают новые таблицы и поля в SQLite."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from tests.test_db_setup import apply_alembic_migrations


def _inspect_migrated_file_db() -> tuple[set[str], set[str]]:
    path = Path("ci_schema_check.db")
    if path.exists():
        path.unlink()
    url = f"sqlite:///{path}"
    apply_alembic_migrations(url)
    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    cols = {c["name"] for c in inspect(engine).get_columns("places")}
    engine.dispose()
    path.unlink(missing_ok=True)
    return tables, cols


def test_migrated_sqlite_has_admin_ops_tables_new() -> None:
    tables, _ = _inspect_migrated_file_db()
    assert {"feature_toggles", "system_logs", "product_events", "admin_operations"}.issubset(tables)


def test_migrated_places_has_address_fields_new() -> None:
    _, cols = _inspect_migrated_file_db()
    assert {
        "address_source",
        "address_confidence",
        "address_updated_at",
        "route_exclusion_reason",
        "admin_comment",
    }.issubset(cols)


def _inspect_migrated_source_observations() -> set[str]:
    path = Path("ci_schema_check_source_observations.db")
    if path.exists():
        path.unlink()
    url = f"sqlite:///{path}"
    apply_alembic_migrations(url)
    engine = create_engine(url)
    cols = {c["name"] for c in inspect(engine).get_columns("source_observations")}
    engine.dispose()
    path.unlink(missing_ok=True)
    return cols


def test_migrated_source_observations_has_provenance_columns_new() -> None:
    cols = _inspect_migrated_source_observations()
    assert {"source_license", "attribution_text", "idempotency_key"}.issubset(cols)
