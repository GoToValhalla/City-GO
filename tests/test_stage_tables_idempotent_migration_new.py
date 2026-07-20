"""
Real PostgreSQL tests proving migration de447288c917 is safe on both a
clean database and a production-shaped database where any subset of its 36
target tables already exists in compatible (or incompatible) form.

Root cause this fixes: a real production deploy failed with
"relation \"place_change_reviews\" already exists" — production's
alembic_version was still 6b9c1e4a8d3f (this migration had never run), yet
place_change_reviews already existed, created outside this Alembic chain
(models/place_change_review.py documents it as a legacy table kept only for
historical schema/data compatibility). The original de447288c917 used
unconditional op.create_table() for all 36 tables and failed loudly instead
of adopting the compatible pre-existing table. See
services/migration_column_guard.py::ensure_table for the idempotent,
ownership-tracked fix (same pattern already proven for column-level drift
by 84665d0fd500/f0c0c48aa12a, tested in
tests/test_place_column_idempotent_migrations_new.py).

By default skipped (so CI/local without a real Postgres server don't fail).
Enable: RUN_STAGE_TABLES_IDEMPOTENT_MIGRATION_SMOKE=1.

Run from the repo root:
  RUN_STAGE_TABLES_IDEMPOTENT_MIGRATION_SMOKE=1 .venv/bin/python -m unittest \
    tests.test_stage_tables_idempotent_migration_new -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = "city_guide_stage_tables_idempotent_fixture"
FIXTURE_DATABASE_URL = f"postgresql+psycopg://user@localhost:5432/{FIXTURE_DB}"

# Production's real reported alembic_version at the time of the failed
# deploy — the revision immediately before de447288c917.
_PRE_MIGRATION_REVISION = "9e1a2b3c4d5f"

_PLACE_CHANGE_REVIEWS_COMPATIBLE_DDL = """
CREATE TABLE place_change_reviews (
    id SERIAL PRIMARY KEY,
    city_id INTEGER NOT NULL REFERENCES cities(id),
    place_id INTEGER NOT NULL REFERENCES places(id),
    field_name VARCHAR(100) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    reason VARCHAR(128) NOT NULL,
    source VARCHAR(64) NOT NULL DEFAULT 'import',
    confidence FLOAT,
    trust_score FLOAT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    reviewed_by VARCHAR(255),
    reviewed_at TIMESTAMP,
    resolution VARCHAR(64),
    review_comment VARCHAR(1000),
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);
"""

_ADMIN_KILL_SWITCHES_COMPATIBLE_DDL = """
CREATE TABLE admin_kill_switches (
    id SERIAL PRIMARY KEY,
    switch_scope VARCHAR(64) NOT NULL,
    target VARCHAR(255),
    action VARCHAR(64) NOT NULL,
    actor VARCHAR(255) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    expires_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL
);
"""


def _should_run() -> bool:
    return os.environ.get("RUN_STAGE_TABLES_IDEMPOTENT_MIGRATION_SMOKE", "").strip() == "1"


def _run_psql(sql: str, *, database: str = "postgres") -> subprocess.CompletedProcess:
    return subprocess.run(
        ["psql", "-U", "user", "-d", database, "-c", sql], capture_output=True, text=True,
    )


def _run_psql_checked(sql: str, *, database: str = "postgres") -> subprocess.CompletedProcess:
    result = _run_psql(sql, database=database)
    assert result.returncode == 0, f"psql failed: {result.stderr}"
    return result


def _alembic(*args: str, timeout: float) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = FIXTURE_DATABASE_URL
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=timeout,
    )


def _table_exists(table: str) -> bool:
    result = _run_psql_checked(
        f"SELECT to_regclass('{table}') IS NOT NULL;", database=FIXTURE_DB,
    )
    return "t" in result.stdout.strip().splitlines()[2].strip().lower() if len(result.stdout.strip().splitlines()) > 2 else False


def _table_comment(table: str) -> str | None:
    result = _run_psql_checked(
        f"SELECT obj_description('{table}'::regclass, 'pg_class');", database=FIXTURE_DB,
    )
    lines = result.stdout.strip().splitlines()
    return lines[2].strip() if len(lines) > 2 and lines[2].strip() else None


def _column_names(table: str) -> set[str]:
    result = _run_psql_checked(
        f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}';",
        database=FIXTURE_DB,
    )
    lines = result.stdout.strip().splitlines()
    return {line.strip() for line in lines[2:-2] if line.strip()}


def _alembic_version() -> str:
    result = _run_psql_checked("SELECT version_num FROM alembic_version;", database=FIXTURE_DB)
    lines = result.stdout.strip().splitlines()
    return lines[2].strip() if len(lines) > 2 else ""


@unittest.skipUnless(
    _should_run(),
    "Set RUN_STAGE_TABLES_IDEMPOTENT_MIGRATION_SMOKE=1 to run these real-Postgres migration tests.",
)
class TestStageTablesIdempotentMigration(unittest.TestCase):
    def setUp(self) -> None:
        _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"')
        _run_psql_checked(f'CREATE DATABASE "{FIXTURE_DB}"')
        self.addCleanup(lambda: _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"'))

    def _migrate_to_pre_revision(self) -> None:
        result = _alembic("upgrade", _PRE_MIGRATION_REVISION, timeout=120)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])

    def test_fresh_empty_database_upgrade_to_head_new(self) -> None:
        result = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")
        for table in ("admin_bulk_operations", "place_change_reviews", "place_snapshots", "ai_candidates"):
            self.assertTrue(_table_exists(table), f"{table} missing after clean upgrade")
            self.assertEqual(
                _table_comment(table), "created_by_revision:de447288c917",
                f"{table} should be owned by this revision on a fresh database",
            )

    def test_production_shaped_database_place_change_reviews_already_exists_new(self) -> None:
        """The exact reproduction of the failed production deploy:
        place_change_reviews pre-exists, in compatible form, created outside
        this Alembic chain; alembic_version is 9e1a2b3c4d5f (never ran this
        migration)."""
        self._migrate_to_pre_revision()
        _run_psql_checked(_PLACE_CHANGE_REVIEWS_COMPATIBLE_DDL, database=FIXTURE_DB)

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}")
        self.assertEqual(_alembic_version(), "de447288c917")
        # Adopted, not recreated: no owner comment, and every pre-existing
        # column is exactly as it was.
        self.assertIsNone(_table_comment("place_change_reviews"))
        self.assertIn("old_value", _column_names("place_change_reviews"))
        self.assertIn("review_comment", _column_names("place_change_reviews"))
        # Every other table in the migration must still be created normally.
        self.assertEqual(_table_comment("admin_bulk_operations"), "created_by_revision:de447288c917")

    def test_partially_populated_schema_mixed_existing_and_missing_new(self) -> None:
        """A mix of two pre-existing compatible tables plus 34 genuinely
        missing tables — proves the fix generalizes beyond the single
        production incident table."""
        self._migrate_to_pre_revision()
        _run_psql_checked(_PLACE_CHANGE_REVIEWS_COMPATIBLE_DDL, database=FIXTURE_DB)
        _run_psql_checked(_ADMIN_KILL_SWITCHES_COMPATIBLE_DDL, database=FIXTURE_DB)

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertIsNone(_table_comment("place_change_reviews"))
        self.assertIsNone(_table_comment("admin_kill_switches"))
        self.assertEqual(_table_comment("admin_bulk_operations"), "created_by_revision:de447288c917")
        self.assertEqual(_table_comment("extraction_candidates"), "created_by_revision:de447288c917")

    def test_incompatible_existing_table_fails_before_mutation_new(self) -> None:
        """An existing place_change_reviews missing columns the model
        expects (a real incompatibility) must fail closed, not silently
        adopt a partial schema."""
        self._migrate_to_pre_revision()
        _run_psql_checked(
            "CREATE TABLE place_change_reviews ("
            "id SERIAL PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities(id), "
            "place_id INTEGER NOT NULL REFERENCES places(id), field_name VARCHAR(100) NOT NULL, "
            "reason INTEGER NOT NULL, source VARCHAR(64) NOT NULL DEFAULT 'import', "
            "status VARCHAR(32) NOT NULL DEFAULT 'pending', "
            "created_at TIMESTAMP NOT NULL DEFAULT now(), updated_at TIMESTAMP NOT NULL DEFAULT now());",
            database=FIXTURE_DB,
        )

        result = _alembic("upgrade", "head", timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("IncompatibleTableError", result.stderr)
        self.assertIn("place_change_reviews", result.stderr)
        self.assertIn("de447288c917", result.stderr)
        # No mutation happened: version unchanged, no later table created.
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION)
        self.assertFalse(_table_exists("admin_bulk_operations"))
        self.assertFalse(_table_exists("extraction_candidates"))

    def test_incompatible_column_type_fails_before_mutation_new(self) -> None:
        """Same as above but with every column present, one with a wrong
        type — proves the type-compatibility check specifically, not just
        the missing-column check."""
        self._migrate_to_pre_revision()
        _run_psql_checked(
            "CREATE TABLE place_change_reviews ("
            "id SERIAL PRIMARY KEY, city_id INTEGER NOT NULL REFERENCES cities(id), "
            "place_id INTEGER NOT NULL REFERENCES places(id), field_name VARCHAR(100) NOT NULL, "
            "old_value JSONB, new_value JSONB, reason INTEGER NOT NULL, "
            "source VARCHAR(64) NOT NULL DEFAULT 'import', confidence FLOAT, trust_score FLOAT, "
            "status VARCHAR(32) NOT NULL DEFAULT 'pending', reviewed_by VARCHAR(255), "
            "reviewed_at TIMESTAMP, resolution VARCHAR(64), review_comment VARCHAR(1000), "
            "created_at TIMESTAMP NOT NULL DEFAULT now(), updated_at TIMESTAMP NOT NULL DEFAULT now());",
            database=FIXTURE_DB,
        )

        result = _alembic("upgrade", "head", timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("IncompatibleTableError", result.stderr)
        self.assertIn("reason", result.stderr)
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION)

    def test_downgrade_preserves_preexisting_table_new(self) -> None:
        """On a production-shaped DB (place_change_reviews pre-existing),
        downgrade must remove only revision-owned tables and leave
        place_change_reviews — and its data — in place."""
        self._migrate_to_pre_revision()
        _run_psql_checked(_PLACE_CHANGE_REVIEWS_COMPATIBLE_DDL, database=FIXTURE_DB)

        upgrade = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(upgrade.returncode, 0, msg=upgrade.stderr[-3000:])

        downgrade = _alembic("downgrade", _PRE_MIGRATION_REVISION, timeout=60)
        self.assertEqual(downgrade.returncode, 0, msg=downgrade.stderr[-3000:])
        self.assertTrue(_table_exists("place_change_reviews"), "pre-existing production table must survive downgrade")
        self.assertFalse(_table_exists("admin_bulk_operations"), "revision-owned table must be removed on downgrade")

        reupgrade = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(reupgrade.returncode, 0, msg=reupgrade.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")
        self.assertIsNone(_table_comment("place_change_reviews"))

    def test_repeated_upgrade_is_a_noop_new(self) -> None:
        first = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(first.returncode, 0, msg=first.stderr[-3000:])
        version_after_first = _alembic_version()

        second = _alembic("upgrade", "head", timeout=30)
        self.assertEqual(second.returncode, 0, msg=second.stderr[-3000:])
        self.assertEqual(_alembic_version(), version_after_first)

    def test_alembic_version_unchanged_after_failure_new(self) -> None:
        self._migrate_to_pre_revision()
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION)

        _run_psql_checked(
            "CREATE TABLE place_change_reviews (id SERIAL PRIMARY KEY, reason INTEGER NOT NULL);",
            database=FIXTURE_DB,
        )
        failed = _alembic("upgrade", "head", timeout=30)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION, "alembic_version must not drift on a failed migration")

        _run_psql_checked("DROP TABLE place_change_reviews;", database=FIXTURE_DB)
        succeeded = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(succeeded.returncode, 0, msg=succeeded.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")

    def test_preflight_detects_scenario_before_deploy_new(self) -> None:
        """scripts/migration_preflight.py, run against this exact
        production-shaped database BEFORE alembic upgrade head, must report
        the pre-existing table as a safe/compatible finding (not
        incompatible) so a deploy pipeline that runs preflight first would
        have proceeded correctly, and must report OK overall."""
        self._migrate_to_pre_revision()
        _run_psql_checked(_PLACE_CHANGE_REVIEWS_COMPATIBLE_DDL, database=FIXTURE_DB)

        env = dict(os.environ)
        env["DATABASE_URL"] = FIXTURE_DATABASE_URL
        result = subprocess.run(
            [sys.executable, "scripts/migration_preflight.py", "--verbose"],
            cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=f"stdout={result.stdout}\nstderr={result.stderr}")
        self.assertIn("RESULT: OK", result.stdout)
        self.assertNotIn("INCOMPATIBLE", result.stdout)


if __name__ == "__main__":
    unittest.main()
