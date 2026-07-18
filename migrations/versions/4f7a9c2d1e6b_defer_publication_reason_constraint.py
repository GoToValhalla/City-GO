"""defer premature publication reason constraint

Revision ID: 4f7a9c2d1e6b
Revises: 8db3c6e1f4a2
Create Date: 2026-07-19

Fresh databases do not receive the Phase 6 constraint from the preceding
reserved revision. Databases that applied the earlier version of that revision
may already contain the constraint; this compensating migration removes it so
all environments converge on the approved pre-Phase-6 schema.
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "4f7a9c2d1e6b"
down_revision = "8db3c6e1f4a2"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_places_publication_reason_consistency"


def _constraint_exists() -> bool:
    inspector = inspect(op.get_bind())
    return any(
        item.get("name") == CONSTRAINT_NAME
        for item in inspector.get_check_constraints("places")
    )


def upgrade() -> None:
    if _constraint_exists():
        with op.batch_alter_table("places") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")


def downgrade() -> None:
    """Do not recreate a constraint whose production preconditions are unverified."""
