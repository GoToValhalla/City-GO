"""add_places_city_foreign_key

Revision ID: c7b36de91a2d
Revises: b21f3c5c1d90
Create Date: 2026-05-25 23:50:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c7b36de91a2d"
down_revision: Union[str, None] = "b21f3c5c1d90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.create_foreign_key(
            "fk_places_city_id_cities",
            "cities",
            ["city_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_constraint("fk_places_city_id_cities", type_="foreignkey")

