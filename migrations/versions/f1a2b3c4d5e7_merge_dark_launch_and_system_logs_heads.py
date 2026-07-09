"""merge dark launch user foundation and system logs index heads

Revision ID: f1a2b3c4d5e7
Revises: b2c3d4e5f6a7, d4e5f6a7b8c9
"""

from typing import Sequence, Union


revision: str = "f1a2b3c4d5e7"
down_revision: Union[str, tuple[str, str], None] = ("b2c3d4e5f6a7", "d4e5f6a7b8c9")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
