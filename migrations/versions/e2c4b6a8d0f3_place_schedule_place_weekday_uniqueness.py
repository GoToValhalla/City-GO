"""Enforce one place_schedules row per (place_id, weekday).

Revision ID: e2c4b6a8d0f3
Revises: f2b3c4d5e6f7
Create Date: 2026-07-22

Duplicate cleanup rule (applied only if duplicates already exist):
for each (place_id, weekday) group, the row with the smallest
(created_at, id) — i.e. the oldest row, ties broken by id — is kept as
authoritative. Every later duplicate row for that same (place_id, weekday)
is deleted. No values are merged; the surviving row's own column values
are left exactly as they already were. This mirrors the winner-selection
rule already established by migrations/versions/c8a91d4e7f20_admin_operation_active_uniqueness.py
(oldest row wins, `created_at ASC, id ASC`).
"""
from __future__ import annotations

from alembic import op

from services.migration_column_guard import drop_index_if_owned, ensure_index

revision = "e2c4b6a8d0f3"
down_revision = "f2b3c4d5e6f7"
branch_labels = None
depends_on = None

_INDEX = "uq_place_schedules_place_weekday"


def upgrade() -> None:
    bind = op.get_bind()
    # Deterministic duplicate cleanup, safe to run even when no duplicates
    # exist (the DELETE then affects zero rows). Oldest row per
    # (place_id, weekday) is authoritative; later duplicates are removed.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY place_id, weekday
                       ORDER BY created_at ASC, id ASC
                   ) AS rn
            FROM place_schedules
        )
        DELETE FROM place_schedules
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    ensure_index(
        bind,
        revision=revision,
        index_name=_INDEX,
        table="place_schedules",
        columns=["place_id", "weekday"],
        unique=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    drop_index_if_owned(bind, revision=revision, table="place_schedules", index_name=_INDEX)
