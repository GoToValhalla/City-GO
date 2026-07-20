"""Add ownership token hashes for route sessions and drafts.

Revision ID: b7e4f1a9082c
Revises: de447288c917
Create Date: 2026-07-21
"""

from __future__ import annotations

import hashlib

import sqlalchemy as sa
from alembic import op

from services.migration_column_guard import drop_column_if_owned, drop_index_if_owned, ensure_column, ensure_index

revision = "b7e4f1a9082c"
down_revision = "de447288c917"
branch_labels = None
depends_on = None


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


def downgrade() -> None:
    bind = op.get_bind()
    drop_index_if_owned(bind, revision=revision, table="route_drafts", index_name="ix_route_drafts_session_token_hash")
    drop_column_if_owned(bind, revision=revision, table="route_drafts", column="session_token_hash")
    drop_index_if_owned(bind, revision=revision, table="route_sessions", index_name="ix_route_sessions_ownership_token_hash")
    drop_column_if_owned(bind, revision=revision, table="route_sessions", column="ownership_token_hash")


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
