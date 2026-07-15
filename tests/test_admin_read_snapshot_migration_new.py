"""Regression coverage for the "relation admin_overview_snapshots does not
exist" production defect.

Root cause: models/admin_read_snapshot.py's three cache tables
(admin_overview_snapshots, admin_city_quality_snapshots,
backlog_queue_snapshots) were only ever created at runtime by
scripts/bootstrap_admin_read_models.py (Table.create(checkfirst=True)) — no
Alembic migration ever created them. Every GET read path already falls back
to a live builder on failure, but services/admin_read_model_v2.refresh_all()
(called by the scheduled admin-read-model-refresh.yml workflow via
scripts/refresh_admin_read_models.py) writes to these tables with no
fallback, so an environment where bootstrap never ran hit UndefinedTable.
Migration 9719aa508caa makes table existence a durable migration guarantee
instead of a best-effort runtime side effect.
"""

from __future__ import annotations

from sqlalchemy import inspect

from db.session import SessionLocal
from models.admin_read_snapshot import AdminOverviewSnapshot, BacklogQueueSnapshot, CityQualitySnapshot
from services.admin_read_model_v2 import refresh_all


def test_admin_read_snapshot_tables_exist_after_migrations_new(db_session) -> None:
    inspector = inspect(db_session.get_bind())
    existing_tables = set(inspector.get_table_names())

    assert AdminOverviewSnapshot.name in existing_tables
    assert CityQualitySnapshot.name in existing_tables
    assert BacklogQueueSnapshot.name in existing_tables


def test_refresh_all_writes_snapshots_without_runtime_bootstrap_new(db_session) -> None:
    """The write path that used to require scripts.bootstrap_admin_read_models
    to run first must now succeed purely from migrated schema."""
    result = refresh_all(db_session)

    assert result["status"] == "refreshed"
    row = db_session.execute(AdminOverviewSnapshot.select()).mappings().first()
    assert row is not None
    assert row["is_dirty"] is False


def test_bootstrap_admin_read_models_is_not_the_only_table_owner_new() -> None:
    """scripts/bootstrap_admin_read_models.py may still run defensively (it is
    checkfirst=True and therefore harmless), but the migration chain — not
    that script — must be what a fresh/production database actually relies
    on. This guards against the tables being removed from the migration
    chain again while the bootstrap script silently keeps masking it."""
    from pathlib import Path

    migrations_dir = Path(__file__).resolve().parents[1] / "migrations" / "versions"
    matches = [
        path
        for path in migrations_dir.glob("*.py")
        if "admin_overview_snapshots" in path.read_text(encoding="utf-8")
    ]
    assert matches, "no Alembic migration creates admin_overview_snapshots"
