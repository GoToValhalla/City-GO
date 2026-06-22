"""merge city publication and import pipeline heads

Revision ID: e2f4a6b8c0d1
Revises: b73c0d1e2f40, d4e5f6a7b8c0
"""

from typing import Sequence, Union


revision: str = "e2f4a6b8c0d1"
down_revision: Union[str, tuple[str, str], None] = ("b73c0d1e2f40", "d4e5f6a7b8c0")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
