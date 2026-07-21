"""Add ownership token hashes for route sessions and drafts.

Historical route_sessions rows predate ownership_token_hash: no raw token was
ever issued for them, so they can never satisfy the hash-based ownership
check. Left as-is, a non-terminal historical session (status active/paused)
would sit forever in a state nobody can ever legitimately reach or mutate
again. This migration explicitly transitions those rows to the existing
terminal `abandoned` status with a deterministic reason recorded in the new
`abandon_reason` column, so historical state is honestly terminal rather than
silently unreachable.

route_drafts.session_token is a one-way SHA-256 hash-and-clear: the raw token
is destroyed in the same UPDATE that populates session_token_hash, so once
upgraded there is no data anywhere from which the raw token could be
reconstructed. downgrade() must not then drop session_token_hash — that
column is the only remaining ownership record for those rows, and once
dropped, ownership of every draft hashed by this migration is permanently and
silently lost. This migration is therefore intentionally irreversible:
downgrade() fails closed with a clear error before touching any schema,
instead of pretending a safe rollback exists.

Revision ID: b7e4f1a9082c
Revises: de447288c917
Create Date: 2026-07-21
"""

from __future__ import annotations

import hashlib

import sqlalchemy as sa
from alembic import op

from services.migration_column_guard import ensure_column, ensure_index

revision = "b7e4f1a9082c"
down_revision = "de447288c917"
branch_labels = None
depends_on = None

_ABANDON_REASON = "invalidated_by_ownership_migration_b7e4f1a9082c"


def upgrade() -> None:
    bind = op.get_bind()
    ensure_column(
        bind,
        revision=revision,
        table="route_sessions",
        column=sa.Column("ownership_token_hash", sa.String(length=64), nullable=True),
    )
    ensure_index(
        bind,
        revision=revision,
        index_name="ix_route_sessions_ownership_token_hash",
        table="route_sessions",
        columns=["ownership_token_hash"],
    )
    ensure_column(
        bind,
        revision=revision,
        table="route_sessions",
        column=sa.Column("abandon_reason", sa.String(length=255), nullable=True),
    )
    ensure_column(
        bind,
        revision=revision,
        table="route_drafts",
        column=sa.Column("session_token_hash", sa.String(length=64), nullable=True),
    )
    ensure_index(
        bind,
        revision=revision,
        index_name="ix_route_drafts_session_token_hash",
        table="route_drafts",
        columns=["session_token_hash"],
    )
    _hash_existing_draft_tokens(bind)
    _abandon_historical_sessions_without_ownership(bind)


def downgrade() -> None:
    raise RuntimeError(
        "b7e4f1a9082c is intentionally irreversible: route_drafts.session_token "
        "was one-way hashed and cleared during upgrade(), so no data exists "
        "anywhere from which the raw token could be restored. Dropping "
        "session_token_hash on downgrade would permanently and silently erase "
        "the only remaining ownership record for every draft this migration "
        "touched. Restore from a pre-upgrade backup instead of downgrading."
    )


def _hash_existing_draft_tokens(bind) -> None:
    rows = bind.execute(
        sa.text(
            "SELECT id, session_token FROM route_drafts "
            "WHERE session_token IS NOT NULL AND TRIM(session_token) <> '' "
            "AND (session_token_hash IS NULL OR TRIM(session_token_hash) = '')"
        )
    ).fetchall()
    for row in rows:
        token = str(row.session_token or "").strip()
        if not token:
            continue
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        bind.execute(
            sa.text(
                "UPDATE route_drafts SET session_token_hash = :digest, session_token = NULL "
                "WHERE id = :id"
            ),
            {"digest": digest, "id": row.id},
        )


def _abandon_historical_sessions_without_ownership(bind) -> None:
    bind.execute(
        sa.text(
            "UPDATE route_sessions SET status = 'abandoned', abandon_reason = :reason "
            "WHERE status NOT IN ('completed', 'abandoned') "
            "AND (ownership_token_hash IS NULL OR TRIM(ownership_token_hash) = '')"
        ),
        {"reason": _ABANDON_REASON},
    )
