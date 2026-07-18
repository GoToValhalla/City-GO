"""add publication reason ledger

Revision ID: 7ca2f5b9e4d1
Revises: 6b9c1e4a8d3f
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "7ca2f5b9e4d1"
down_revision = "6b9c1e4a8d3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "places",
        sa.Column("publication_reason_code", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "places",
        sa.Column(
            "publication_reason_details",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.create_index(
        "ix_places_publication_reason_code",
        "places",
        ["publication_reason_code"],
        unique=False,
    )
    op.create_index(
        "ix_places_publication_status_reason",
        "places",
        ["publication_status", "publication_reason_code"],
        unique=False,
    )

    op.create_table(
        "place_publication_transitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("reason_details", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("human_comment", sa.Text(), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("correlation_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_place_publication_transitions_place_id",
        "place_publication_transitions",
        ["place_id"],
        unique=False,
    )
    op.create_index(
        "ix_place_publication_transitions_place_created",
        "place_publication_transitions",
        ["place_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_place_publication_transitions_reason_code",
        "place_publication_transitions",
        ["reason_code"],
        unique=False,
    )
    op.create_index(
        "ix_place_publication_transitions_correlation_id",
        "place_publication_transitions",
        ["correlation_id"],
        unique=False,
    )

    # Honest initialisation: old non-public rows have no provable transition cause.
    op.execute(
        "UPDATE places SET publication_reason_code = 'legacy_unknown' "
        "WHERE publication_status <> 'published' AND publication_reason_code IS NULL"
    )
    op.execute(
        "INSERT INTO place_publication_transitions "
        "(place_id, from_status, to_status, reason_code, reason_details, human_comment, actor, source, correlation_id, created_at) "
        "SELECT id, publication_status, publication_status, 'legacy_unknown', '{}', publication_comment, "
        "'system:backfill', 'migration_backfill', NULL, CURRENT_TIMESTAMP "
        "FROM places WHERE publication_status <> 'published'"
    )

    # The strict state/reason CHECK is intentionally deferred to a later
    # migration. It may only be enabled after every legacy mutation path uses
    # the canonical writer and the backfill has been verified in production.


def downgrade() -> None:
    op.drop_index(
        "ix_place_publication_transitions_correlation_id",
        table_name="place_publication_transitions",
    )
    op.drop_index(
        "ix_place_publication_transitions_reason_code",
        table_name="place_publication_transitions",
    )
    op.drop_index(
        "ix_place_publication_transitions_place_created",
        table_name="place_publication_transitions",
    )
    op.drop_index(
        "ix_place_publication_transitions_place_id",
        table_name="place_publication_transitions",
    )
    op.drop_table("place_publication_transitions")
    op.drop_index("ix_places_publication_status_reason", table_name="places")
    op.drop_index("ix_places_publication_reason_code", table_name="places")
    op.drop_column("places", "publication_reason_details")
    op.drop_column("places", "publication_reason_code")
