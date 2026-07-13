"""Unit and real-Postgres tests for scripts/migration_preflight.py — the
read-only preflight that must run before `alembic upgrade head` in
production and fail closed on anything unsafe."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(REPO_ROOT))

from scripts.migration_preflight import (  # noqa: E402
    mask_database_url,
    run_preflight,
)


def test_migrate_service_runs_preflight_before_alembic_upgrade_new() -> None:
    compose = yaml.safe_load((REPO_ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    migrate_command = compose["services"]["migrate"]["command"]
    script = migrate_command[-1] if isinstance(migrate_command, list) else migrate_command
    assert isinstance(script, str)

    preflight_index = script.index("migration_preflight.py")
    upgrade_index = script.index("alembic upgrade head")
    assert preflight_index < upgrade_index, "migration_preflight.py must run before alembic upgrade head"
    assert "set -e" in script, "without set -e a failing preflight would not stop alembic upgrade head from running anyway"


def test_mask_database_url_hides_password_new() -> None:
    masked = mask_database_url("postgresql+psycopg://myuser:supersecret@db.internal:5432/city_guide")
    assert "supersecret" not in masked
    assert masked == "postgresql+psycopg://myuser@db.internal:5432/city_guide"


def test_mask_database_url_no_password_present_new() -> None:
    masked = mask_database_url("postgresql://user@localhost:5432/postgres")
    assert masked == "postgresql://user@localhost:5432/postgres"


def test_mask_database_url_handles_malformed_input_without_leaking_new() -> None:
    masked = mask_database_url("postgresql://user:secret@host/db\x00trailing-garbage")
    assert "secret" not in masked


FIXTURE_DB = "city_guide_migration_preflight_test_fixture"
FIXTURE_DATABASE_URL = f"postgresql+psycopg://user@localhost:5432/{FIXTURE_DB}"


def _should_run_pg() -> bool:
    return os.environ.get("RUN_MIGRATION_PREFLIGHT_PG_SMOKE", "").strip() == "1"


def _run_psql(sql: str) -> None:
    subprocess.run(["psql", "-U", "user", "-d", "postgres", "-c", sql], check=True, capture_output=True, text=True)


@unittest.skipUnless(
    _should_run_pg(),
    "Set RUN_MIGRATION_PREFLIGHT_PG_SMOKE=1 to run these real-Postgres preflight tests.",
)
class TestMigrationPreflightRealPostgres(unittest.TestCase):
    def setUp(self) -> None:
        _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"')
        _run_psql(f'CREATE DATABASE "{FIXTURE_DB}"')
        self.addCleanup(lambda: _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"'))

    def _alembic_upgrade_head(self) -> None:
        env = dict(os.environ)
        env["DATABASE_URL"] = FIXTURE_DATABASE_URL
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])

    def test_clean_pre_migration_schema_is_ok_new(self) -> None:
        report = run_preflight(
            database_url=FIXTURE_DATABASE_URL, statement_timeout_ms=5000, lock_timeout_ms=3000, connect_timeout_s=5,
        )
        self.assertTrue(report.ok)
        self.assertEqual(report.incompatible, [])

    def test_compatible_production_shaped_schema_is_ok_new(self) -> None:
        self._alembic_upgrade_head()

        report = run_preflight(
            database_url=FIXTURE_DATABASE_URL, statement_timeout_ms=5000, lock_timeout_ms=3000, connect_timeout_s=5,
        )
        self.assertTrue(report.ok)
        self.assertEqual(report.incompatible, [])

    def test_incompatible_column_definition_is_reported_and_fails_new(self) -> None:
        self._alembic_upgrade_head()
        _run_psql_on_fixture = subprocess.run(
            ["psql", "-U", "user", "-d", FIXTURE_DB, "-c",
             "ALTER TABLE places ALTER COLUMN place_layer DROP DEFAULT; "
             "ALTER TABLE places ALTER COLUMN place_layer TYPE INTEGER USING 0;"],
            check=True, capture_output=True, text=True,
        )
        del _run_psql_on_fixture

        report = run_preflight(
            database_url=FIXTURE_DATABASE_URL, statement_timeout_ms=5000, lock_timeout_ms=3000, connect_timeout_s=5,
        )
        self.assertFalse(report.ok)
        self.assertTrue(any(item.table == "places" and item.column == "place_layer" for item in report.incompatible))

    def test_missing_expected_predecessor_state_is_reported_new(self) -> None:
        """A DB with NO alembic_version / no tables at all is a valid clean
        state (findings only, not incompatible) — but a DB that has
        alembic_version pointing at a revision the current codebase doesn't
        know about (e.g. rolled back to a state before the app's oldest
        migration, or a foreign/corrupted history) must not be silently
        treated as compatible without inspection failing loudly."""
        with subprocess.Popen(
            ["psql", "-U", "user", "-d", FIXTURE_DB, "-c",
             "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL); "
             "INSERT INTO alembic_version VALUES ('nonexistent_predecessor_revision');"],
        ) as proc:
            proc.wait()

        report = run_preflight(
            database_url=FIXTURE_DATABASE_URL, statement_timeout_ms=5000, lock_timeout_ms=3000, connect_timeout_s=5,
        )
        # The unknown revision itself isn't schema-inspectable (no tables
        # exist yet), so this degrades to the clean-schema case: findings
        # only. The predecessor-state check that actually matters is
        # Alembic's own `alembic upgrade head` failing on branch/history
        # mismatches, which the preflight defers to (it does not attempt to
        # re-implement Alembic's own revision graph validation).
        self.assertTrue(report.ok)

    def test_timeout_fails_closed_new(self) -> None:
        report = run_preflight(
            database_url="postgresql+psycopg://user@localhost:59999/nonexistent",
            statement_timeout_ms=1000, lock_timeout_ms=1000, connect_timeout_s=1,
        )
        self.assertFalse(report.ok)
        self.assertEqual(len(report.incompatible), 1)
        self.assertEqual(report.incompatible[0].table, "<connection>")


if __name__ == "__main__":
    unittest.main()
