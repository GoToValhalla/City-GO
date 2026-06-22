"""add city quality metadata fields

Revision ID: f0a1b2c3d4e6
Revises: f9a2b3c4d5e6
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "f0a1b2c3d4e6"
down_revision: Union[str, None] = "f9a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_json = JSONB().with_variant(JSON(), "sqlite")


def upgrade() -> None:
    with op.batch_alter_table("cities") as batch_op:
        batch_op.add_column(sa.Column("primary_language", sa.String(16), nullable=False, server_default="ru"))
        batch_op.add_column(sa.Column("secondary_languages", _json, nullable=True))
        batch_op.add_column(sa.Column("osm_relation_id", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("boundary", _json, nullable=True))
        batch_op.add_column(sa.Column("readiness_score", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("quality_status", sa.String(32), nullable=False, server_default="not_ready"))
        batch_op.add_column(sa.Column("last_import_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("next_import_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("population_tier", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("expected_places_count", sa.Integer(), nullable=True))
        batch_op.create_index("ix_cities_primary_language", ["primary_language"])
        batch_op.create_index("ix_cities_osm_relation_id", ["osm_relation_id"])
        batch_op.create_index("ix_cities_readiness_score", ["readiness_score"])
        batch_op.create_index("ix_cities_quality_status", ["quality_status"])
        batch_op.create_index("ix_cities_population_tier", ["population_tier"])


def downgrade() -> None:
    with op.batch_alter_table("cities") as batch_op:
        batch_op.drop_index("ix_cities_population_tier")
        batch_op.drop_index("ix_cities_quality_status")
        batch_op.drop_index("ix_cities_readiness_score")
        batch_op.drop_index("ix_cities_osm_relation_id")
        batch_op.drop_index("ix_cities_primary_language")
        batch_op.drop_column("expected_places_count")
        batch_op.drop_column("population_tier")
        batch_op.drop_column("next_import_at")
        batch_op.drop_column("last_import_at")
        batch_op.drop_column("quality_status")
        batch_op.drop_column("readiness_score")
        batch_op.drop_column("boundary")
        batch_op.drop_column("osm_relation_id")
        batch_op.drop_column("secondary_languages")
        batch_op.drop_column("primary_language")
