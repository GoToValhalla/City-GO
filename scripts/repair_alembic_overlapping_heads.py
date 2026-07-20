"""Diagnose overlapping Alembic heads. Never mutates alembic_version.

Historical repair once deleted revision 9d0e1f2a3b4c when both
9d0e1f2a3b4c and fb7e3c2a91d4 were present. That rewrite is forbidden:
fix overlapping heads with an Alembic merge revision instead.
"""

from __future__ import annotations

import sys

from sqlalchemy import Engine, create_engine, inspect, text

from core.config import settings

LEGACY_ANCESTOR_REVISION = "9d0e1f2a3b4c"
CURRENT_DESCENDANT_REVISION = "fb7e3c2a91d4"
OVERLAP = frozenset({LEGACY_ANCESTOR_REVISION, CURRENT_DESCENDANT_REVISION})


def detect_overlapping_heads(engine: Engine) -> bool:
    """Return True when the historical overlapping pair is present."""
    if not inspect(engine).has_table("alembic_version"):
        return False
    with engine.connect() as connection:
        revisions = set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
    return OVERLAP.issubset(revisions)


def repair_overlapping_heads(engine: Engine) -> bool:
    """Compatibility wrapper: diagnose only, never DELETE from alembic_version."""
    return detect_overlapping_heads(engine)


def main() -> int:
    engine = create_engine(settings.database_url)
    if detect_overlapping_heads(engine):
        print(
            "UNSAFE: overlapping legacy heads detected "
            f"{sorted(OVERLAP)}. Do not DELETE from alembic_version. "
            "Apply an Alembic merge revision / operator-reviewed repair."
        )
        return 1
    if not inspect(engine).has_table("alembic_version"):
        print("alembic_version missing — nothing to diagnose")
        return 0
    with engine.connect() as connection:
        revisions = sorted(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
    print(f"ok: alembic_version={revisions}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
