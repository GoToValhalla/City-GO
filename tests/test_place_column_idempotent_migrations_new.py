"""
Real PostgreSQL tests proving migrations 84665d0fd500 and
f0c0c48aa12a are safe on both a clean database and a production-shaped
database where any subset of their target columns already exists in
compatible (or incompatible) form.

Root cause this fixes: a real production deploy (e150f85) failed with
"column canonical_category of relation places already exists" — that
column existed on production in compatible form, created outside this
Alembic chain, but 84665d0fd500's upgrade() unconditionally ran
ALTER TABLE ... ADD COLUMN for it. See services/migration_column_guard.py
for the idempotent, ownership-tracked implementation.

By default skipped (so CI/local without a real Postgres server don't
fail). Enable: RUN_PLACE_COLUMN_IDEMPOTENT_MIGRATIONS_SMOKE=1.

Run from the repo root:
  RUN_PLACE_COLUMN_IDEMPOTENT_MIGRATIONS_SMOKE=1 .venv/bin/python -m unittest \
    tests.test_place_column_idempotent_migrations_new -v
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = "city_guide_place_column_idempotent_fixture"
FIXTURE_DATABASE_URL = f"postgresql+psycopg://user@localhost:5432/{FIXTURE_DB}"

_PRE_MIGRATION_REVISION = "d4e6f8a0b2c4"  # revision immediately before 84665d0fd500


def _should_run() -> bool:
    return os.environ.get("RUN_PLACE_COLUMN_IDEMPOTENT_MIGRATIONS_SMOKE", "").strip() == "1"


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


def _column_comment(column: str) -> str | None:
    result = _run_psql_checked(
        "SELECT col_description('places'::regclass, "
        f"(SELECT attnum FROM pg_attribute WHERE attrelid='places'::regclass AND attname='{column}'));",
        database=FIXTURE_DB,
    )
    value = result.stdout.strip().splitlines()
    # psql -c default output includes a header/dashes/row/footer; the row is line 3 (index 2).
    return value[2].strip() if len(value) > 2 and value[2].strip() else None


def _column_exists(column: str) -> bool:
    result = _run_psql_checked(
        f"SELECT 1 FROM information_schema.columns WHERE table_name='places' AND column_name='{column}';",
        database=FIXTURE_DB,
    )
    return "1 row" in result.stdout or "(1 " in result.stdout


def _alembic_version() -> str:
    result = _run_psql_checked("SELECT version_num FROM alembic_version;", database=FIXTURE_DB)
    lines = result.stdout.strip().splitlines()
    return lines[2].strip() if len(lines) > 2 else ""


@unittest.skipUnless(
    _should_run(),
    "Set RUN_PLACE_COLUMN_IDEMPOTENT_MIGRATIONS_SMOKE=1 to run these real-Postgres migration tests.",
)
class TestPlaceColumnIdempotentMigrations(unittest.TestCase):
    def setUp(self) -> None:
        _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"')
        _run_psql_checked(f'CREATE DATABASE "{FIXTURE_DB}"')
        self.addCleanup(lambda: _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"'))

    def _migrate_to_pre_revision(self) -> None:
        result = _alembic("upgrade", _PRE_MIGRATION_REVISION, timeout=120)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])

    def test_clean_db_upgrade_to_head_new(self) -> None:
        result = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")
        for column in ("canonical_category", "lifecycle_status", "quality_score", "is_spam_poi", "is_duplicate_suspected", "geo_precision"):
            self.assertTrue(_column_exists(column), f"{column} missing after clean upgrade")

    def test_all_target_columns_already_exist_compatibly_new(self) -> None:
        """Every column both migrations would add is pre-created, in
        compatible form, before they run — the exact 'entire subset already
        exists' case."""
        self._migrate_to_pre_revision()
        _run_psql_checked(
            "ALTER TABLE places "
            "ADD COLUMN canonical_category VARCHAR(100), "
            "ADD COLUMN lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'active', "
            "ADD COLUMN quality_tier VARCHAR(32) NOT NULL DEFAULT 'silver', "
            "ADD COLUMN quality_score INTEGER NOT NULL DEFAULT 65, "
            "ADD COLUMN completeness_score INTEGER NOT NULL DEFAULT 0, "
            "ADD COLUMN photo_score INTEGER NOT NULL DEFAULT 0, "
            "ADD COLUMN description_score INTEGER NOT NULL DEFAULT 0, "
            "ADD COLUMN confidence_score INTEGER NOT NULL DEFAULT 0, "
            "ADD COLUMN freshness_score INTEGER NOT NULL DEFAULT 3, "
            "ADD COLUMN is_spam_poi BOOLEAN NOT NULL DEFAULT false, "
            "ADD COLUMN is_duplicate_suspected BOOLEAN NOT NULL DEFAULT false, "
            "ADD COLUMN geo_precision VARCHAR(32), "
            "ADD COLUMN critical_field_expired BOOLEAN NOT NULL DEFAULT false;",
            database=FIXTURE_DB,
        )

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")
        # Pre-existing columns must not carry an owner comment — the
        # migrations must not have re-created them.
        self.assertIsNone(_column_comment("canonical_category"))
        self.assertIsNone(_column_comment("is_duplicate_suspected"))

    def test_only_canonical_category_already_exists_new(self) -> None:
        """The exact production incident: only canonical_category
        pre-exists; everything else must still be created normally."""
        self._migrate_to_pre_revision()
        _run_psql_checked("ALTER TABLE places ADD COLUMN canonical_category VARCHAR(100);", database=FIXTURE_DB)

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertIsNone(_column_comment("canonical_category"))
        self.assertEqual(_column_comment("lifecycle_status"), "created_by_revision:84665d0fd500")
        self.assertEqual(_column_comment("is_duplicate_suspected"), "created_by_revision:f0c0c48aa12a")

    def test_arbitrary_partial_subset_already_exists_new(self) -> None:
        """A different, arbitrary partial subset spanning both migrations —
        proves the fix generalizes beyond the exact incident column."""
        self._migrate_to_pre_revision()
        _run_psql_checked(
            "ALTER TABLE places "
            "ADD COLUMN quality_tier VARCHAR(32) NOT NULL DEFAULT 'silver', "
            "ADD COLUMN is_spam_poi BOOLEAN NOT NULL DEFAULT false, "
            "ADD COLUMN geo_precision VARCHAR(32);",
            database=FIXTURE_DB,
        )

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])
        self.assertIsNone(_column_comment("quality_tier"))
        self.assertIsNone(_column_comment("is_spam_poi"))
        self.assertIsNone(_column_comment("geo_precision"))
        self.assertEqual(_column_comment("canonical_category"), "created_by_revision:84665d0fd500")
        self.assertEqual(_column_comment("is_duplicate_suspected"), "created_by_revision:f0c0c48aa12a")

    def test_incompatible_existing_type_fails_before_mutation_new(self) -> None:
        self._migrate_to_pre_revision()
        _run_psql_checked("ALTER TABLE places ADD COLUMN canonical_category INTEGER;", database=FIXTURE_DB)

        result = _alembic("upgrade", "head", timeout=60)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("IncompatibleColumnError", result.stderr)
        self.assertIn("canonical_category", result.stderr)
        self.assertIn("84665d0fd500", result.stderr)
        # No mutation happened: version unchanged, no later column created.
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION)
        self.assertFalse(_column_exists("lifecycle_status"))

    def test_incompatible_nullability_fails_before_mutation_new(self) -> None:
        """A NOT NULL column with no server_default whose existing form is
        nullable is a real incompatibility (see
        services/migration_column_guard.py::ensure_column). Simulated here
        directly against the guard function rather than via a real
        migration file, since every actual migration column in this chain
        that is NOT NULL already carries a server_default (verified: this
        exact scenario cannot be produced by 84665d0fd500/f0c0c48aa12a as
        currently written) — this proves the guard's own fail-fast branch
        works, independent of which migration might one day exercise it."""
        self._migrate_to_pre_revision()
        _run_psql_checked("ALTER TABLE places ADD COLUMN test_not_null_no_default VARCHAR(10);", database=FIXTURE_DB)

        env = dict(os.environ)
        env["DATABASE_URL"] = FIXTURE_DATABASE_URL
        script = (
            "import sqlalchemy as sa\n"
            "from sqlalchemy import create_engine\n"
            "from services.migration_column_guard import ensure_column, IncompatibleColumnError\n"
            "engine = create_engine('" + FIXTURE_DATABASE_URL + "')\n"
            "with engine.begin() as conn:\n"
            "    try:\n"
            "        ensure_column(conn, revision='test-rev', table='places', "
            "column=sa.Column('test_not_null_no_default', sa.String(length=10), nullable=False))\n"
            "        print('NO_ERROR_RAISED')\n"
            "    except IncompatibleColumnError as exc:\n"
            "        print('RAISED:' + str(exc))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", script], cwd=str(REPO_ROOT), env=env, capture_output=True, text=True, timeout=30,
        )
        self.assertIn("RAISED:", result.stdout, msg=f"stdout={result.stdout} stderr={result.stderr}")
        self.assertIn("test_not_null_no_default", result.stdout)

    def test_production_shaped_upgrade_reaches_head_new(self) -> None:
        """The exact reproduction of the failed deploy: migrate to the
        revision right before 84665d0fd500 in one process, inject
        canonical_category exactly as it existed in production, then
        upgrade head in a fresh process."""
        self._migrate_to_pre_revision()
        _run_psql_checked("ALTER TABLE places ADD COLUMN canonical_category VARCHAR(100);", database=FIXTURE_DB)

        result = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(result.returncode, 0, msg=f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}")
        self.assertEqual(_alembic_version(), "de447288c917")

    def test_repeated_upgrade_is_a_noop_new(self) -> None:
        first = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(first.returncode, 0, msg=first.stderr[-3000:])
        version_after_first = _alembic_version()

        second = _alembic("upgrade", "head", timeout=30)
        self.assertEqual(second.returncode, 0, msg=second.stderr[-3000:])
        self.assertEqual(_alembic_version(), version_after_first)

    def test_downgrade_reupgrade_remains_safe_new(self) -> None:
        """On a production-shaped DB (canonical_category pre-existing),
        downgrade must remove only revision-owned columns and leave
        canonical_category in place; re-upgrade must then succeed again."""
        self._migrate_to_pre_revision()
        _run_psql_checked("ALTER TABLE places ADD COLUMN canonical_category VARCHAR(100);", database=FIXTURE_DB)

        upgrade = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(upgrade.returncode, 0, msg=upgrade.stderr[-3000:])

        downgrade = _alembic("downgrade", _PRE_MIGRATION_REVISION, timeout=60)
        self.assertEqual(downgrade.returncode, 0, msg=downgrade.stderr[-3000:])
        self.assertTrue(_column_exists("canonical_category"), "pre-existing production column must survive downgrade")
        self.assertFalse(_column_exists("lifecycle_status"), "revision-owned column must be removed on downgrade")

        reupgrade = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(reupgrade.returncode, 0, msg=reupgrade.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")
        self.assertIsNone(_column_comment("canonical_category"))

    def test_no_isolated_connection_deadlock_new(self) -> None:
        """Same reproduction shape as the earlier a1c2d3e4f5b6/b2d4f6a8c3e5
        deadlock: migrate to just before this pair in one process, then the
        rest of the way in a fresh process, with a bounded timeout — a
        second-connection deadlock would hang until the timeout kills it."""
        self._migrate_to_pre_revision()
        result = _alembic("upgrade", "head", timeout=30)
        self.assertEqual(result.returncode, 0, msg=f"stdout={result.stdout[-2000:]} stderr={result.stderr[-2000:]}")

    def test_alembic_version_correct_after_success_and_unchanged_after_failure_new(self) -> None:
        self._migrate_to_pre_revision()
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION)

        _run_psql_checked("ALTER TABLE places ADD COLUMN canonical_category INTEGER;", database=FIXTURE_DB)
        failed = _alembic("upgrade", "head", timeout=30)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(_alembic_version(), _PRE_MIGRATION_REVISION, "alembic_version must not drift on a failed migration")

        _run_psql_checked("ALTER TABLE places DROP COLUMN canonical_category;", database=FIXTURE_DB)
        succeeded = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(succeeded.returncode, 0, msg=succeeded.stderr[-3000:])
        self.assertEqual(_alembic_version(), "de447288c917")


if __name__ == "__main__":
    unittest.main()
