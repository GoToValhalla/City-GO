"""preserve published city visibility during refresh imports

Revision ID: f1a8c4d9e602
Revises: e5f7a9b3d202
Create Date: 2026-06-24
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f1a8c4d9e602"
down_revision: Union[str, None] = "e5f7a9b3d202"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_TRIGGER_FUNCTION = "preserve_published_city_during_import"
_TRIGGER_NAME = "trg_preserve_published_city_during_import"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_TRIGGER_FUNCTION}()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.is_active IS TRUE
               AND OLD.launch_status = 'published'
               AND NEW.launch_status IN ('importing', 'imported', 'review_required', 'import_failed') THEN
                NEW.is_active := TRUE;
                NEW.launch_status := 'published';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {_TRIGGER_NAME}
        BEFORE UPDATE OF launch_status, is_active ON cities
        FOR EACH ROW
        EXECUTE FUNCTION {_TRIGGER_FUNCTION}();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(f"DROP TRIGGER IF EXISTS {_TRIGGER_NAME} ON cities")
    op.execute(f"DROP FUNCTION IF EXISTS {_TRIGGER_FUNCTION}()")
