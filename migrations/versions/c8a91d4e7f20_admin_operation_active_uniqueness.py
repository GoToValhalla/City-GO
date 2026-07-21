"""Enforce one active admin operation per type and city scope.

Revision ID: c8a91d4e7f20
Revises: b7e4f1a9082c
Create Date: 2026-07-21
"""

from __future__ import annotations

from alembic import op

revision = "c8a91d4e7f20"
down_revision = "b7e4f1a9082c"
branch_labels = None
depends_on = None

_INDEX = "uq_admin_operations_active_scope"


def upgrade() -> None:
    # Preserve the oldest active operation as authoritative and terminate any
    # pre-existing duplicates before installing the database invariant.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY operation_type, COALESCE(city_slug, '')
                       ORDER BY created_at ASC, id ASC
                   ) AS rn
            FROM admin_operations
            WHERE status IN ('queued', 'running')
        )
        UPDATE admin_operations
        SET status = 'cancelled',
            error_message = 'Cancelled during active-operation uniqueness migration',
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.execute(
        f"""
        CREATE UNIQUE INDEX {_INDEX}
        ON admin_operations (operation_type, COALESCE(city_slug, ''))
        WHERE status IN ('queued', 'running')
        """
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {_INDEX}")
