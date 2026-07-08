"""add composite index on system_logs(city_slug, module, created_at)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from __future__ import annotations

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("system_logs") as batch_op:
        batch_op.create_index("ix_system_logs_city_module_created", ["city_slug", "module", "created_at"])


def downgrade() -> None:
    with op.batch_alter_table("system_logs") as batch_op:
        batch_op.drop_index("ix_system_logs_city_module_created")
