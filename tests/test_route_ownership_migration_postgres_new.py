from __future__ import annotations

import hashlib
import os

import pytest

from tests.ownership_migration_pg_support import (
    HEAD,
    PREDECESSOR,
    alembic,
    drop_database,
    execute,
    recreate_database,
    scalar,
)

pytestmark = pytest.mark.skipif(
    not os.getenv("ROUTE_OWNERSHIP_MIGRATION_POSTGRES"),
    reason="requires explicit PostgreSQL migration harness",
)


def test_route_ownership_migration_postgres_new() -> None:
    recreate_database()
    try:
        alembic(HEAD)
        assert scalar("SELECT version_num FROM alembic_version") == HEAD

        alembic("downgrade")
        execute("INSERT INTO route_drafts (city_id, session_token, random_seed) VALUES (1, 'legacy-token', 7)")
        alembic(HEAD)
        expected = hashlib.sha256(b"legacy-token").hexdigest()
        assert scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=7") == expected
        assert scalar("SELECT session_token IS NULL FROM route_drafts WHERE random_seed=7") is True
        alembic(HEAD)
        assert scalar("SELECT version_num FROM alembic_version") == HEAD

        alembic("downgrade")
        execute("INSERT INTO route_drafts (city_id, session_token, random_seed) VALUES (1, 'rollback-token', 8)")
        execute("""
        CREATE FUNCTION fail_token_clear() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'injected backfill failure'; END $$;
        CREATE TRIGGER fail_token_clear BEFORE UPDATE ON route_drafts
        FOR EACH ROW WHEN (OLD.session_token IS NOT NULL) EXECUTE FUNCTION fail_token_clear();
        """)
        failed = alembic(HEAD, check=False)
        assert failed.returncode != 0
        assert scalar("SELECT version_num FROM alembic_version") == PREDECESSOR
        assert scalar("SELECT session_token FROM route_drafts WHERE random_seed=8") == "rollback-token"
        assert scalar(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='route_drafts' AND column_name='session_token_hash'"
        ) == 0
    finally:
        drop_database()
