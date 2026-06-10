"""init_place_model

Revision ID: e48f13974bc8
Revises:
Create Date: 2026-03-23 20:45:58.142394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e48f13974bc8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'places',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('city_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('short_description', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('outdoor', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('indoor', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('dog_friendly', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('family_friendly', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('price_level', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_places_id'), 'places', ['id'], unique=False)
    op.create_index(op.f('ix_places_city_id'), 'places', ['city_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_places_city_id'), table_name='places')
    op.drop_index(op.f('ix_places_id'), table_name='places')
    op.drop_table('places')
