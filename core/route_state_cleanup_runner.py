from __future__ import annotations

from db.session import SessionLocal
from services.route_state_cleanup_service import (
    ROUTE_STATE_CLEANUP_BATCH_SIZE,
    cleanup_expired_route_states,
)


def run_route_state_cleanup_once(*, limit: int = ROUTE_STATE_CLEANUP_BATCH_SIZE) -> int:
    """Run one bounded cleanup batch in its own short-lived transaction."""
    db = SessionLocal()
    try:
        deleted = cleanup_expired_route_states(db, limit=limit)
        db.commit()
        return deleted
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()
