"""append-only place publication ledger FK and triggers

Revision ID: 9e1a2b3c4d5f
Revises: 4f7a9c2d1e6b
Create Date: 2026-07-20

Replace cascade FK with RESTRICT and reject UPDATE/DELETE on the ledger.
Does not enable the strict publication-reason CHECK.
"""

from __future__ import annotations

from alembic import op

revision = "9e1a2b3c4d5f"
down_revision = "4f7a9c2d1e6b"
branch_labels = None
depends_on = None

_FK_NAME = "fk_place_publication_transitions_place_id_restrict"
_NO_UPDATE_FN = "reject_place_publication_transition_update"
_NO_DELETE_FN = "reject_place_publication_transition_delete"
_NO_UPDATE_TRG = "trg_place_publication_transitions_no_update"
_NO_DELETE_TRG = "trg_place_publication_transitions_no_delete"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite tests rely on ORM create_all DDL triggers in the model module.
        return

    op.execute(
        """
        DO $$
        DECLARE
            fk_name text;
        BEGIN
            FOR fk_name IN
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                JOIN pg_namespace nsp ON nsp.oid = rel.relnamespace
                WHERE nsp.nspname = current_schema()
                  AND rel.relname = 'place_publication_transitions'
                  AND con.contype = 'f'
                  AND pg_get_constraintdef(con.oid) LIKE '%REFERENCES places%'
            LOOP
                EXECUTE format(
                    'ALTER TABLE place_publication_transitions DROP CONSTRAINT %I',
                    fk_name
                );
            END LOOP;
        END
        $$;
        """
    )
    op.create_foreign_key(
        _FK_NAME,
        "place_publication_transitions",
        "places",
        ["place_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_NO_UPDATE_FN}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'place publication transition ledger is append-only';
        END;
        $$;
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {_NO_DELETE_FN}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'place publication transition ledger is append-only';
        END;
        $$;
        """
    )
    op.execute(
        f"""
        DROP TRIGGER IF EXISTS {_NO_UPDATE_TRG} ON place_publication_transitions;
        CREATE TRIGGER {_NO_UPDATE_TRG}
        BEFORE UPDATE ON place_publication_transitions
        FOR EACH ROW
        EXECUTE PROCEDURE {_NO_UPDATE_FN}();
        """
    )
    op.execute(
        f"""
        DROP TRIGGER IF EXISTS {_NO_DELETE_TRG} ON place_publication_transitions;
        CREATE TRIGGER {_NO_DELETE_TRG}
        BEFORE DELETE ON place_publication_transitions
        FOR EACH ROW
        EXECUTE PROCEDURE {_NO_DELETE_FN}();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(f"DROP TRIGGER IF EXISTS {_NO_UPDATE_TRG} ON place_publication_transitions")
    op.execute(f"DROP TRIGGER IF EXISTS {_NO_DELETE_TRG} ON place_publication_transitions")
    op.execute(f"DROP FUNCTION IF EXISTS {_NO_UPDATE_FN}()")
    op.execute(f"DROP FUNCTION IF EXISTS {_NO_DELETE_FN}()")

    op.drop_constraint(_FK_NAME, "place_publication_transitions", type_="foreignkey")
    op.create_foreign_key(
        "place_publication_transitions_place_id_fkey",
        "place_publication_transitions",
        "places",
        ["place_id"],
        ["id"],
        ondelete="CASCADE",
    )
