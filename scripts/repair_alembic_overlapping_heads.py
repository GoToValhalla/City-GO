"""Repair the historical Alembic version-table overlap created by joined heads."""

from __future__ import annotations

from sqlalchemy import Engine, inspect, text

LEGACY_ANCESTOR_REVISION = "9d0e1f2a3b4c"
CURRENT_DESCENDANT_REVISION = "fb7e3c2a91d4"


def repair_overlapping_heads(engine: Engine) -> bool:
    """Remove the redundant ancestor marker when both joined revisions are stored."""
    if not inspect(engine).has_table("alembic_version"):
        return False

    with engine.begin() as connection:
        revisions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        expected_pair = {LEGACY_ANCESTOR_REVISION, CURRENT_DESCENDANT_REVISION}
        if not expected_pair.issubset(revisions):
            return False

        connection.execute(
            text("DELETE FROM alembic_version WHERE version_num = :revision"),
            {"revision": LEGACY_ANCESTOR_REVISION},
        )
    return True


def main() -> None:
    from db.session import engine

    repaired = repair_overlapping_heads(engine)
    print("Alembic overlapping heads repaired" if repaired else "Alembic version table needs no repair")


if __name__ == "__main__":
    main()
