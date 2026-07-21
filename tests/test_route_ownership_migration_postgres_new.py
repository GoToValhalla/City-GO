from __future__ import annotations

import hashlib
import os

import pytest

from tests.ownership_migration_pg_support import (
    OWNERSHIP_REVISION,
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


def test_route_ownership_migration_upgrade_hashes_legacy_draft_tokens_new() -> None:
    """Upgrade succeeds and legacy plaintext route_drafts.session_token is
    hashed into session_token_hash, with the raw token cleared."""
    recreate_database()
    try:
        alembic(PREDECESSOR)
        execute("INSERT INTO route_drafts (city_id, session_token, random_seed) VALUES (1, 'legacy-token', 7)")

        alembic(OWNERSHIP_REVISION)
        assert scalar("SELECT version_num FROM alembic_version") == OWNERSHIP_REVISION

        expected = hashlib.sha256(b"legacy-token").hexdigest()
        assert scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=7") == expected
        assert scalar("SELECT session_token IS NULL FROM route_drafts WHERE random_seed=7") is True

        # Re-running upgrade at head is a no-op: same hash, no crash.
        alembic(OWNERSHIP_REVISION)
        assert scalar("SELECT version_num FROM alembic_version") == OWNERSHIP_REVISION
        assert scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=7") == expected
    finally:
        drop_database()


def test_route_ownership_migration_ownership_validation_works_after_upgrade_new() -> None:
    """After upgrade, ownership_tokens_match must accept the correct raw
    token against the stored hash and reject an incorrect one."""
    from services.anonymous_ownership import hash_ownership_token, ownership_tokens_match

    recreate_database()
    try:
        alembic(PREDECESSOR)
        execute("INSERT INTO route_drafts (city_id, session_token, random_seed) VALUES (1, 'legacy-token-2', 9)")
        alembic(OWNERSHIP_REVISION)

        stored_hash = scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=9")
        assert stored_hash == hash_ownership_token("legacy-token-2")
        assert ownership_tokens_match("legacy-token-2", stored_hash) is True
        assert ownership_tokens_match("wrong-token", stored_hash) is False
    finally:
        drop_database()


def test_route_ownership_migration_downgrade_fails_safely_and_leaves_schema_intact_new() -> None:
    """downgrade() must be intentionally irreversible: it fails closed with a
    clear error, before any destructive DDL, and leaves the upgraded schema
    and hashed data completely intact — no partial downgrade."""
    recreate_database()
    try:
        alembic(PREDECESSOR)
        execute("INSERT INTO route_drafts (city_id, session_token, random_seed) VALUES (1, 'rollback-token', 8)")
        alembic(OWNERSHIP_REVISION)
        expected = hashlib.sha256(b"rollback-token").hexdigest()
        assert scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=8") == expected

        failed = alembic("downgrade", check=False)
        assert failed.returncode != 0
        assert "irreversible" in (failed.stdout + failed.stderr).lower()

        # No partial downgrade: still at the ownership revision, schema and
        # data both fully intact.
        assert scalar("SELECT version_num FROM alembic_version") == OWNERSHIP_REVISION
        assert scalar("SELECT session_token_hash FROM route_drafts WHERE random_seed=8") == expected
        assert scalar(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='route_drafts' AND column_name='session_token_hash'"
        ) == 1
        assert scalar(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name='route_sessions' AND column_name='ownership_token_hash'"
        ) == 1
    finally:
        drop_database()


def test_route_ownership_migration_abandons_historical_sessions_without_hash_new() -> None:
    """Historical route_sessions rows (no ownership_token_hash, since no raw
    token was ever issued for them pre-migration) must be explicitly
    transitioned to the terminal `abandoned` status with a recorded reason
    -- active/paused/completed historical rows all get the correct outcome."""
    recreate_database()
    try:
        alembic(PREDECESSOR)
        execute(
            "INSERT INTO routes (id, city_id, slug, title, is_active, created_at, updated_at) "
            "VALUES (101, 1, 'hist-route', 'Historical Route', true, now(), now())"
        )
        execute(
            "INSERT INTO route_sessions (id, route_id, status, current_point_index, "
            "visited_point_indexes, skipped_point_indexes, started_at, created_at, updated_at) VALUES "
            "(201, 101, 'active', 0, '[]', '[]', now(), now(), now()),"
            "(202, 101, 'paused', 0, '[]', '[]', now(), now(), now()),"
            "(203, 101, 'completed', 3, '[]', '[]', now(), now(), now()),"
            "(204, 101, 'abandoned', 0, '[]', '[]', now(), now(), now())"
        )

        alembic(OWNERSHIP_REVISION)

        assert scalar("SELECT status FROM route_sessions WHERE id=201") == "abandoned"
        assert scalar("SELECT status FROM route_sessions WHERE id=202") == "abandoned"
        assert scalar("SELECT status FROM route_sessions WHERE id=203") == "completed"
        assert scalar("SELECT status FROM route_sessions WHERE id=204") == "abandoned"
        assert scalar("SELECT abandon_reason FROM route_sessions WHERE id=201") is not None
        # Pre-existing terminal rows must not be rewritten with the migration reason.
        assert scalar("SELECT abandon_reason FROM route_sessions WHERE id=203") is None
    finally:
        drop_database()
