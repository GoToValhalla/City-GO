"""known missing poi registry

Revision ID: a6c1d8e9f304
Revises: e5f7a9b3d202
"""

from alembic import op
import sqlalchemy as sa


revision = "a6c1d8e9f304"
down_revision = "e5f7a9b3d202"
branch_labels = None
depends_on = None

JSON = sa.JSON()


def upgrade() -> None:
    op.create_table(
        "known_missing_poi",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("matched_place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("name_local", sa.String(255), nullable=True),
        sa.Column("name_en", sa.String(255), nullable=True),
        sa.Column("name_ru", sa.String(255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("coordinate_precision", sa.String(32), nullable=False, server_default="approximate"),
        sa.Column("expected_category", sa.String(64), nullable=False),
        sa.Column("expected_scope", sa.String(64), nullable=False),
        sa.Column("expected_route_policy", sa.String(64), nullable=False, server_default="must_have"),
        sa.Column("significance", sa.String(64), nullable=False, server_default="local"),
        sa.Column("source", sa.String(64), nullable=False, server_default="manual_seed"),
        sa.Column("external_refs", JSON, nullable=True),
        sa.Column("reporter_note", sa.Text(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="missing"),
        sa.Column("gap_reason", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("city_id", "slug", name="uq_known_missing_poi_city_slug"),
    )
    op.create_index("ix_known_missing_poi_city_id", "known_missing_poi", ["city_id"])
    op.create_index("ix_known_missing_poi_matched_place_id", "known_missing_poi", ["matched_place_id"])
    op.create_index("ix_known_missing_poi_slug", "known_missing_poi", ["slug"])
    op.create_index("ix_known_missing_poi_status", "known_missing_poi", ["status"])
    op.create_index("ix_known_missing_poi_gap_reason", "known_missing_poi", ["gap_reason"])
    op.create_index("ix_known_missing_poi_expected_category", "known_missing_poi", ["expected_category"])
    op.create_index("ix_known_missing_poi_expected_scope", "known_missing_poi", ["expected_scope"])
    op.create_index("ix_known_missing_poi_expected_route_policy", "known_missing_poi", ["expected_route_policy"])
    op.create_index("ix_known_missing_poi_significance", "known_missing_poi", ["significance"])
    op.create_index("ix_known_missing_poi_source", "known_missing_poi", ["source"])


def downgrade() -> None:
    for index_name in (
        "ix_known_missing_poi_source",
        "ix_known_missing_poi_significance",
        "ix_known_missing_poi_expected_route_policy",
        "ix_known_missing_poi_expected_scope",
        "ix_known_missing_poi_expected_category",
        "ix_known_missing_poi_gap_reason",
        "ix_known_missing_poi_status",
        "ix_known_missing_poi_slug",
        "ix_known_missing_poi_matched_place_id",
        "ix_known_missing_poi_city_id",
    ):
        op.drop_index(index_name, table_name="known_missing_poi")
    op.drop_table("known_missing_poi")
