"""defer premature publication reason constraint

Revision ID: 4f7a9c2d1e6b
Revises: 8db3c6e1f4a2
Create Date: 2026-07-19

Upgrade removes the prematurely deployed Phase 6 constraint. Downgrade restores
the historical schema only after a fail-closed consistency preflight.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "4f7a9c2d1e6b"
down_revision = "8db3c6e1f4a2"
branch_labels = None
depends_on = None

CONSTRAINT_NAME = "ck_places_publication_reason_consistency"
CONSTRAINT_SQL = (
    "(publication_status = 'published' AND publication_reason_code IS NULL) "
    "OR (publication_status <> 'published' AND publication_reason_code IS NOT NULL)"
)


def _constraint_exists() -> bool:
    return any(
        item.get("name") == CONSTRAINT_NAME
        for item in inspect(op.get_bind()).get_check_constraints("places")
    )


def _inconsistent_count() -> int:
    value = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM places "
            "WHERE (publication_status = 'published' AND publication_reason_code IS NOT NULL) "
            "OR (publication_status <> 'published' AND publication_reason_code IS NULL)"
        )
    ).scalar()
    return int(value or 0)


def upgrade() -> None:
    if _constraint_exists():
        with op.batch_alter_table("places") as batch_op:
            batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")


def downgrade() -> None:
    if _constraint_exists():
        return
    inconsistent = _inconsistent_count()
    if inconsistent:
        raise RuntimeError(
            "Cannot restore historical publication constraint: "
            f"{inconsistent} inconsistent places remain"
        )
    with op.batch_alter_table("places") as batch_op:
        batch_op.create_check_constraint(CONSTRAINT_NAME, CONSTRAINT_SQL)
