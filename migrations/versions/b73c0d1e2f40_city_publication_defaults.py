"""safe defaults for city publication

Revision ID: b73c0d1e2f40
Revises: fa21b0c7d9e2
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b73c0d1e2f40"
down_revision: Union[str, None] = "fa21b0c7d9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("cities", "launch_status", server_default="draft")
    op.alter_column("cities", "is_active", server_default=sa.false())
    op.alter_column("places", "is_published", server_default=sa.false())
    op.alter_column("places", "is_visible_in_catalog", server_default=sa.false())
    op.alter_column("places", "is_route_eligible", server_default=sa.false())
    op.alter_column("places", "is_searchable", server_default=sa.false())
    op.alter_column("places", "publication_status", server_default="draft")

    op.execute(
        """
        UPDATE cities
        SET is_active = false,
            updated_at = now()
        WHERE launch_status IN ('draft', 'importing', 'imported', 'review_required', 'import_failed', 'unpublished')
        """
    )


def downgrade() -> None:
    op.alter_column("cities", "launch_status", server_default="published")
    op.alter_column("cities", "is_active", server_default=sa.true())
    op.alter_column("places", "is_published", server_default=sa.true())
    op.alter_column("places", "is_visible_in_catalog", server_default=sa.true())
    op.alter_column("places", "is_route_eligible", server_default=sa.true())
    op.alter_column("places", "is_searchable", server_default=sa.true())
    op.alter_column("places", "publication_status", server_default="published")
