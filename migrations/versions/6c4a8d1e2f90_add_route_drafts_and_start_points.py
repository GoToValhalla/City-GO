"""add route drafts and city start points"""

import sqlalchemy as sa
from alembic import op

revision = "6c4a8d1e2f90"
down_revision = "e2f4a6b8c0d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "city_start_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("label_ru", sa.String(255), nullable=False),
        sa.Column("label_en", sa.String(255), nullable=True),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False, server_default="city_center"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
    )
    _drafts()
    _points()
    _indexes()
    _seed_city_centers()


def _drafts() -> None:
    op.create_table(
        "route_drafts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("session_token", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("route_status", sa.String(32), nullable=False, server_default="partial"),
        sa.Column("start_lat", sa.Float(), nullable=True),
        sa.Column("start_lng", sa.Float(), nullable=True),
        sa.Column("start_label", sa.String(255), nullable=True),
        sa.Column("start_type", sa.String(32), nullable=False, server_default="city_center"),
        sa.Column("budget_minutes", sa.Integer(), nullable=False, server_default="120"),
        sa.Column("total_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("selected_category_slugs", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("category_mode", sa.String(32), nullable=False, server_default="none"),
        sa.Column("user_removed_place_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("warnings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("edit_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
    )


def _points() -> None:
    op.create_table(
        "route_draft_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_id", sa.Integer(), sa.ForeignKey("route_drafts.id"), nullable=False),
        sa.Column("place_id", sa.Integer(), sa.ForeignKey("places.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("user_locked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("inserted_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("replacement_of_place_id", sa.Integer(), nullable=True),
        sa.Column("walk_minutes_from_prev", sa.Integer(), nullable=True),
        sa.Column("walk_minutes_to_next", sa.Integer(), nullable=True),
        sa.Column("visit_minutes", sa.Integer(), nullable=False, server_default="35"),
        sa.Column("open_status", sa.String(32), nullable=False, server_default="unknown"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.current_timestamp()),
    )


def _indexes() -> None:
    op.create_index("ix_city_start_points_city_id", "city_start_points", ["city_id"])
    op.create_index("ix_route_drafts_city_id", "route_drafts", ["city_id"])
    op.create_index("ix_route_drafts_session_token", "route_drafts", ["session_token"])
    op.create_index("ix_route_draft_points_draft_id", "route_draft_points", ["draft_id"])


def _seed_city_centers() -> None:
    op.execute(
        """
        INSERT INTO city_start_points (city_id, label_ru, label_en, lat, lng, type, sort_order, is_active)
        SELECT id, 'Центр города', 'City center', center_lat, center_lng, 'city_center', 0, TRUE
        FROM cities
        WHERE center_lat IS NOT NULL AND center_lng IS NOT NULL
        """
    )


def downgrade() -> None:
    tuple(map(op.drop_table, ("route_draft_points", "route_drafts", "city_start_points")))