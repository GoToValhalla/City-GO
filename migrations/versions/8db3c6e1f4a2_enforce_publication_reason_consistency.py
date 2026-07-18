"""enforce publication reason consistency

Revision ID: 8db3c6e1f4a2
Revises: 7ca2f5b9e4d1
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

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
    bind = op.get_bind()
    inconsistent_count = int(
        bind.execute(
            sa.text(
                "SELECT COUNT(*) FROM places "
                "WHERE (publication_status = 'published' AND publication_reason_code IS NOT NULL) "
                "OR (publication_status <> 'published' AND publication_reason_code IS NULL)"
            )
        ).scalar()
        or 0
    )
    if inconsistent_count:
        raise RuntimeError(
            "Cannot enable publication reason consistency constraint: "
            f"{inconsistent_count} inconsistent places remain"
        )

    with op.batch_alter_table("places") as batch_op:
        batch_op.create_check_constraint(CONSTRAINT_NAME, CONSTRAINT_SQL)


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
