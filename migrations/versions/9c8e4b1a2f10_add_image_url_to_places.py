"""add_image_url_to_places

Revision ID: 9c8e4b1a2f10
Revises: 3fb51e7943f5
Create Date: 2026-04-03 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Уникальный идентификатор миграции.
revision: str = "9c8e4b1a2f10"

# Предыдущая миграция в цепочке.
down_revision: Union[str, None] = "3fb51e7943f5"

# Дополнительные Alembic-поля.
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем поле image_url в таблицу places.
    op.add_column("places", sa.Column("image_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    # Удаляем поле image_url при откате миграции.
    op.drop_column("places", "image_url")
