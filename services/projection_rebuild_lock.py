"""Database-owned serialization for conflicting projection rebuilds."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def serialize_projection_rebuilds(db: Session) -> None:
    """Hold a transaction-scoped PostgreSQL table lock through replacement.

    The lock serializes global and city jobs together, so a stale city worker
    cannot publish over a newer global generation. SQLite test transactions are
    already single-writer and need no extra statement.
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("LOCK TABLE projection_rebuild_jobs IN SHARE ROW EXCLUSIVE MODE"))
