"""review_queue_items: partial unique index for one open item

Root cause (CITYGO review-queue audit): uq_review_item_open included
`status` in its key (place_id, field_name, reason, status). That does not
enforce "at most one open item per logical problem" -- two OPEN rows with
different reasons already race past it (see the companion race-safe-insert
fix in services/review_queue_service.py and services/publication_policy.py),
and worse, it actively collides on the RESOLVED side: two rows that share
(place_id, field_name, reason) and both reach status="resolved" (e.g. the
same field re-flagged and resolved across two separate import/enrichment
cycles) violate this constraint and raise IntegrityError on resolve.

The fix is a genuine partial unique index scoped to open work only:
    UNIQUE (place_id, field_name, reason) WHERE status IN ('open', 'pending')
Multiple resolved historical rows with the same identity remain allowed --
this is required audit history, not a duplicate to be prevented.

Before creating the index this migration checks for existing rows that
would violate it (more than one open/pending row sharing the same
place_id/field_name/reason) and fails closed with a clear error naming the
offending place/field/reason combinations, rather than silently deleting or
merging any moderation history. An operator must resolve or reassign the
conflicting rows first; see the error message for the exact query used.

No existing rows are deleted, merged, or rewritten by this migration.

Revision ID: a4c6e8f0b2d4
Revises: e2c4b6a8d0f3
Create Date: 2026-07-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a4c6e8f0b2d4"
down_revision = "e2c4b6a8d0f3"
branch_labels = None
depends_on = None

OLD_CONSTRAINT_NAME = "uq_review_item_open"
NEW_INDEX_NAME = "uq_review_queue_items_open_identity"


class ConflictingOpenReviewItemsError(RuntimeError):
    """Raised when existing data would violate the new partial unique
    index; the migration must fail before any DDL runs, never silently
    delete or merge review history to make room for the constraint."""


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    conflicts = bind.execute(
        sa.text(
            "SELECT place_id, field_name, reason, COUNT(*) AS open_count "
            "FROM review_queue_items "
            "WHERE status IN ('open', 'pending') "
            "GROUP BY place_id, field_name, reason "
            "HAVING COUNT(*) > 1"
        )
    ).fetchall()
    if conflicts:
        rows = ", ".join(
            f"(place_id={row.place_id}, field_name={row.field_name!r}, reason={row.reason!r}, open_count={row.open_count})"
            for row in conflicts
        )
        raise ConflictingOpenReviewItemsError(
            "Cannot create uq_review_queue_items_open_identity: "
            f"{len(conflicts)} (place_id, field_name, reason) combination(s) already have more than one "
            f"open/pending review_queue_items row: {rows}. Resolve or reassign the extra open rows for "
            "each combination (they are not deleted or merged automatically) before re-running this "
            "migration."
        )

    existing_constraints = {uc["name"] for uc in inspector.get_unique_constraints("review_queue_items")}
    if OLD_CONSTRAINT_NAME in existing_constraints:
        with op.batch_alter_table("review_queue_items") as batch_op:
            batch_op.drop_constraint(OLD_CONSTRAINT_NAME, type_="unique")

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("review_queue_items")}
    if NEW_INDEX_NAME not in existing_indexes:
        op.create_index(
            NEW_INDEX_NAME,
            "review_queue_items",
            ["place_id", "field_name", "reason"],
            unique=True,
            postgresql_where=sa.text("status IN ('open', 'pending')"),
            sqlite_where=sa.text("status IN ('open', 'pending')"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_indexes = {ix["name"] for ix in inspector.get_indexes("review_queue_items")}
    if NEW_INDEX_NAME in existing_indexes:
        op.drop_index(NEW_INDEX_NAME, table_name="review_queue_items")

    existing_constraints = {uc["name"] for uc in inspector.get_unique_constraints("review_queue_items")}
    if OLD_CONSTRAINT_NAME not in existing_constraints:
        with op.batch_alter_table("review_queue_items") as batch_op:
            batch_op.create_unique_constraint(OLD_CONSTRAINT_NAME, ["place_id", "field_name", "reason", "status"])
