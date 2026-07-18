"""reserve final publication consistency rollout phase

Revision ID: 8db3c6e1f4a2
Revises: 7ca2f5b9e4d1
Create Date: 2026-07-18

This revision intentionally does not create the strict CHECK constraint.  The
constraint is a separate final rollout action after repository-wide mutation
migration, production backfill verification, PostgreSQL concurrency tests and
full CI have all succeeded.  Keeping this revision as a no-op preserves the
already-published Alembic graph without enabling Phase 6 prematurely.
"""

from __future__ import annotations

revision = "8db3c6e1f4a2"
down_revision = "7ca2f5b9e4d1"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_places_publication_reason_consistency"
CONSTRAINT_SQL = (
    "(publication_status = 'published' AND publication_reason_code IS NULL) "
    "OR (publication_status <> 'published' AND publication_reason_code IS NOT NULL)"
)


def upgrade() -> None:
    """Reserve the revision; strict enforcement remains deliberately disabled."""


def downgrade() -> None:
    """No schema change was made by upgrade()."""
