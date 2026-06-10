"""add_category_id_to_places"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a31a10f9e37"
down_revision: Union[str, None] = "1e31cbdc17df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("category_id", sa.Integer(), nullable=True))

    op.execute(
        """
        UPDATE places
        SET category_id = (
            SELECT categories.id
            FROM categories
            WHERE places.category = categories.code
        )
        """
    )

    op.create_index(op.f("ix_places_category_id"), "places", ["category_id"], unique=False)

    # SQLite не поддерживает ALTER ADD CONSTRAINT — нужен batch mode.
    with op.batch_alter_table("places") as batch_op:
        batch_op.create_foreign_key(
            "fk_places_category_id_categories",
            "categories",
            ["category_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_constraint("fk_places_category_id_categories", type_="foreignkey")
    op.drop_index(op.f("ix_places_category_id"), table_name="places")
    op.drop_column("places", "category_id")
