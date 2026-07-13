"""
Migration safety smoke on a disposable, production-shaped PostgreSQL
database — regression for a real, reproducible deadlock found during a
publication-safety audit.

By default skipped (so CI/local without a real Postgres server don't fail).
Enable: RUN_MIGRATION_PRODUCTION_SHAPED_SMOKE=1 and a working local
Postgres superuser-ish role able to CREATE DATABASE / DROP DATABASE (uses a
throwaway DB name, never touches an existing database).

Run from the repo root:
  RUN_MIGRATION_PRODUCTION_SHAPED_SMOKE=1 .venv/bin/python -m unittest \
    tests.test_migration_production_shaped_safety_smoke -v

Root cause reproduced here: migrations a1c2d3e4f5b6 and b2d4f6a8c3e5 used to
repair source_observations schema at migration time by calling
services.import_pipeline.schema_compat.ensure_import_pipeline_schema(engine)
— which always opens a brand-new pooled connection via engine.connect(),
never Alembic's own already-open migration connection/transaction. On a
"production-shaped" database — migrated up through d4e6f8a0b2c4 the normal
first-time way but never past a1c2d3e4f5b6 in one continuous run (the
realistic shape of a database that was migrated once and is now being
migrated again, in a fresh process, after other tables were already
touched) — that second connection deterministically deadlocks against
locks Alembic's own transaction holds from earlier migrations in the same
upgrade run. A clean, from-scratch, single continuous `alembic upgrade
head` never hit this (that's how the original E2E rehearsal DB was
created), which is exactly why the original manual rehearsal never
surfaced it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DB = "city_guide_migration_safety_smoke_fixture"
BASE_DATABASE_URL = os.environ.get("MIGRATION_SMOKE_BASE_DATABASE_URL", "postgresql://user@localhost:5432/postgres")
FIXTURE_DATABASE_URL = f"postgresql+psycopg://user@localhost:5432/{FIXTURE_DB}"


def _should_run() -> bool:
    return os.environ.get("RUN_MIGRATION_PRODUCTION_SHAPED_SMOKE", "").strip() == "1"


def _run_psql(sql: str) -> None:
    subprocess.run(["psql", "-U", "user", "-d", "postgres", "-c", sql], check=True, capture_output=True, text=True)


def _alembic(*args: str, timeout: float) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = FIXTURE_DATABASE_URL
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@unittest.skipUnless(
    _should_run(),
    "Set RUN_MIGRATION_PRODUCTION_SHAPED_SMOKE=1 to run this real-Postgres migration safety smoke (see module docstring).",
)
class TestMigrationProductionShapedSafety(unittest.TestCase):
    def setUp(self) -> None:
        _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"')
        _run_psql(f'CREATE DATABASE "{FIXTURE_DB}"')
        self.addCleanup(lambda: _run_psql(f'DROP DATABASE IF EXISTS "{FIXTURE_DB}"'))

    def test_upgrade_head_from_scratch_completes_new(self) -> None:
        result = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(result.returncode, 0, msg=result.stderr[-3000:])

    def test_upgrade_head_from_production_shaped_state_does_not_deadlock_new(self) -> None:
        """The exact reproduction: migrate to the revision right before the
        two-migration pair that used to deadlock, in ITS OWN process (a
        fresh connection pool, simulating a real second `alembic upgrade`
        invocation against an already-partially-migrated production
        database), then upgrade the rest of the way in another fresh
        process. Both steps must complete well within the timeout — a
        deadlock here would hang until the timeout kills it."""
        first = _alembic("upgrade", "d4e6f8a0b2c4", timeout=120)
        self.assertEqual(first.returncode, 0, msg=first.stderr[-3000:])

        second = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(
            second.returncode, 0,
            msg=(
                "Migration hung or failed on a production-shaped DB — "
                f"stdout={second.stdout[-2000:]} stderr={second.stderr[-2000:]}"
            ),
        )

    def test_downgrade_and_reupgrade_across_the_fixed_pair_is_reversible_new(self) -> None:
        upgrade_all = _alembic("upgrade", "head", timeout=120)
        self.assertEqual(upgrade_all.returncode, 0, msg=upgrade_all.stderr[-3000:])

        downgrade = _alembic("downgrade", "c9d0e1f2a3b4", timeout=60)
        self.assertEqual(downgrade.returncode, 0, msg=downgrade.stderr[-3000:])

        reupgrade = _alembic("upgrade", "head", timeout=60)
        self.assertEqual(reupgrade.returncode, 0, msg=reupgrade.stderr[-3000:])


if __name__ == "__main__":
    unittest.main()
