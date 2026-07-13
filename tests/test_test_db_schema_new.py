"""Проверка: alembic-миграции создают новые таблицы и поля в SQLite."""

from pathlib import Path

from sqlalchemy import create_engine, inspect

from models.place import Place
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


def test_migrated_places_has_every_place_model_column_new() -> None:
    """Regression for the E2E rehearsal's Defect #3: models/place.py defined
    canonical_category, lifecycle_status, quality_tier, quality_score and 6
    other columns that no migration ever shipped, so any ORM query selecting
    a Place (e.g. import_pipeline's collection COUNT queries) failed with
    UndefinedColumn on a database migrated from scratch. Diff every column
    the Place model declares against what a from-scratch migration run
    actually creates, so a newly added model column without a matching
    migration fails this test immediately instead of surfacing later as a
    runtime UndefinedColumn during a real import."""
    _, cols = _inspect_migrated_file_db()
    model_columns = {column.name for column in Place.__table__.columns}
    assert model_columns.issubset(cols)
