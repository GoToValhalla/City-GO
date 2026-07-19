"""defer premature publication reason constraint

Revision ID: 4f7a9c2d1e6b
Revises: 8db3c6e1f4a2
Create Date: 2026-07-19

Upgrade removes the prematurely deployed Phase 6 constraint when it exists.
The current parent revision is a no-op, therefore downgrade must also leave the
constraint absent. Phase 6 may only be enabled by a future dedicated migration
after its production preconditions are verified.
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
    return any(
        item.get("name") == CONSTRAINT_NAME
        for item in inspect(op.get_bind()).get_check_constraints("places")
    )


def upgrade() -> None:
    if _constraint_exists():
        with op.batch_alter_table("places") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")


def downgrade() -> None:
    """Parent revision is a no-op; never recreate unverified Phase 6 enforcement."""
