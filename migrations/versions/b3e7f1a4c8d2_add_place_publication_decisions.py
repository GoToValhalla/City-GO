"""add place_publication_decisions table

STAGE 2 VALIDATION BLOCKER FIX: models/place_publication_decision.py's
PlacePublicationDecision model was added by commit 96e7bb0 ("Add
publication policy decision model") without a matching Alembic migration.
services/canonical_publication_apply.py::apply_canonical_publication_verdict
writes to this table via _record_decision() on EVERY place processed by
the import pipeline (mid-pipeline apply_publication_decisions step and
finalize_import_publication) — a real production database migrated only
via `alembic upgrade head` (as docker-compose's migrate service does) is
missing this table and any import would fail on the first place it
processes. This was masked in every test run because tests/conftest.py's
engine fixture uses Base.metadata.create_all(), which creates every ORM
table regardless of whether a migration exists for it.

Verified: on a clean sqlite DB, `alembic upgrade head` before this
migration does NOT create place_publication_decisions; after this
migration it does.

Revision ID: b3e7f1a4c8d2
Revises: a1f3c9d2e4b7
Create Date: 2026-07-16 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b3e7f1a4c8d2"
down_revision = "a1f3c9d2e4b7"
branch_labels = None
depends_on = None


def _json_type():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return sa.JSON()
    return postgresql.JSONB()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "place_publication_decisions" in inspector.get_table_names():
        return

    op.create_table(
        "place_publication_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("place_id", sa.Integer(), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="shadow"),
        sa.Column("decision", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="recorded"),
        sa.Column("trust_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("failed_gates", _json_type(), nullable=True),
        sa.Column("review_reasons", _json_type(), nullable=True),
        sa.Column("payload", _json_type(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["place_id"], ["places.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_place_publication_decisions_city_id"), "place_publication_decisions", ["city_id"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_place_id"), "place_publication_decisions", ["place_id"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_mode"), "place_publication_decisions", ["mode"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_decision"), "place_publication_decisions", ["decision"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_status"), "place_publication_decisions", ["status"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_trust_score"), "place_publication_decisions", ["trust_score"], unique=False)
    op.create_index(op.f("ix_place_publication_decisions_created_at"), "place_publication_decisions", ["created_at"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "place_publication_decisions" in inspector.get_table_names():
        op.drop_table("place_publication_decisions")
