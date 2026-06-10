"""add_slug_to_places"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "784d6d2f3828"
down_revision: Union[str, None] = "d7f42a463fe3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала добавляем slug как nullable, чтобы миграция прошла на существующих данных.
    op.add_column("places", sa.Column("slug", sa.String(length=255), nullable=True))

    # Заполняем slug для уже существующих записей.
    op.execute("UPDATE places SET slug = 'place-' || id WHERE slug IS NULL")

    # SQLite не поддерживает ALTER COLUMN SET NOT NULL — нужен batch mode (copy-and-move).
    with op.batch_alter_table("places") as batch_op:
        batch_op.alter_column(
            "slug",
            existing_type=sa.String(length=255),
            nullable=False,
        )

    # Добавляем уникальный индекс для быстрых запросов и защиты от дублей.
    op.create_index(op.f("ix_places_slug"), "places", ["slug"], unique=True)


def downgrade() -> None:
    # Удаляем индекс и колонку slug при откате миграции.
    op.drop_index(op.f("ix_places_slug"), table_name="places")
    op.drop_column("places", "slug")
