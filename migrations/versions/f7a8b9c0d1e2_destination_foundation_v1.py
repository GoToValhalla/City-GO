"""Destination foundation v1 tables and place extensions.

Revision ID: f7a8b9c0d1e2
Revises: e6a1b2c3d4f5
"""

from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "e6a1b2c3d4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("destination_type", sa.String(length=64), server_default="city", nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("legacy_city_id", sa.Integer(), nullable=True),
        sa.Column("center_lat", sa.Float(), nullable=True),
        sa.Column("center_lng", sa.Float(), nullable=True),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("boundary", sa.JSON(), nullable=True),
        sa.Column("launch_status", sa.String(length=64), server_default="draft", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("readiness_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["legacy_city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_destinations_slug", "destinations", ["slug"], unique=True)
    op.create_index("ix_destinations_destination_type", "destinations", ["destination_type"])
    op.create_index("ix_destinations_launch_status", "destinations", ["launch_status"])
    op.create_index("ix_destinations_is_published", "destinations", ["is_published"])
    op.create_index("ix_destinations_parent_id", "destinations", ["parent_id"])
    op.create_index("ix_destinations_legacy_city_id", "destinations", ["legacy_city_id"])

    op.create_table(
        "destination_scopes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope_type", sa.String(length=64), server_default="all", nullable=False),
        sa.Column("import_strategy", sa.String(length=64), server_default="single_bbox", nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=True),
        sa.Column("polygon", sa.JSON(), nullable=True),
        sa.Column("import_profile", sa.String(length=64), server_default="tourist_core", nullable=False),
        sa.Column("is_walkable_cluster", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_imported_at", sa.DateTime(), nullable=True),
        sa.Column("next_run_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("destination_id", "code", name="uq_destination_scope_code"),
    )
    op.create_index("ix_destination_scopes_destination_id", "destination_scopes", ["destination_id"])
    op.create_index("ix_destination_scopes_enabled", "destination_scopes", ["enabled"])
    op.create_index("ix_destination_scopes_next_run_at", "destination_scopes", ["next_run_at"])

    op.create_table(
        "destination_place_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("assignment_type", sa.String(length=64), server_default="legacy_city", nullable=False),
        sa.Column("confidence", sa.Float(), server_default="1.0", nullable=False),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scope_id"], ["destination_scopes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("place_id", "destination_id", name="uq_place_destination_membership"),
    )
    op.create_index("ix_dpm_place_id", "destination_place_memberships", ["place_id"])
    op.create_index("ix_dpm_destination_id", "destination_place_memberships", ["destination_id"])
    op.create_index("ix_dpm_is_primary", "destination_place_memberships", ["is_primary"])
    op.create_index("ix_dpm_destination_hidden", "destination_place_memberships", ["destination_id", "is_hidden"])
    op.create_index("ix_dpm_destination_place", "destination_place_memberships", ["destination_id", "place_id"])

    op.create_table(
        "destination_membership_conflicts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("destination_id", sa.Integer(), nullable=False),
        sa.Column("scope_ids", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(length=128), server_default="overlapping_scopes", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dmc_place_id", "destination_membership_conflicts", ["place_id"])
    op.create_index("ix_dmc_destination_id", "destination_membership_conflicts", ["destination_id"])
    op.create_index("ix_dmc_status", "destination_membership_conflicts", ["status"])

    with op.batch_alter_table("places") as batch_op:
        batch_op.add_column(sa.Column("primary_destination_id", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("destination_assignment_stale", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        batch_op.create_foreign_key(
            "fk_places_primary_destination_id",
            "destinations",
            ["primary_destination_id"],
            ["id"],
        )
        batch_op.create_index("ix_places_primary_destination_id", ["primary_destination_id"])
        batch_op.create_index("ix_places_destination_assignment_stale", ["destination_assignment_stale"])


def downgrade() -> None:
    with op.batch_alter_table("places") as batch_op:
        batch_op.drop_index("ix_places_destination_assignment_stale")
        batch_op.drop_index("ix_places_primary_destination_id")
        batch_op.drop_constraint("fk_places_primary_destination_id", type_="foreignkey")
        batch_op.drop_column("destination_assignment_stale")
        batch_op.drop_column("primary_destination_id")
    op.drop_table("destination_membership_conflicts")
    op.drop_table("destination_place_memberships")
    op.drop_table("destination_scopes")
    op.drop_table("destinations")
