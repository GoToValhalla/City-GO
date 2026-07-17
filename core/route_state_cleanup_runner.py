from __future__ import annotations

import logging
from time import monotonic

from db.session import SessionLocal
from services.route_state_cleanup_service import (
    ROUTE_STATE_CLEANUP_BATCH_SIZE,
    cleanup_expired_route_states,
)

logger = logging.getLogger(__name__)


def run_route_state_cleanup_once(*, limit: int = ROUTE_STATE_CLEANUP_BATCH_SIZE) -> int:
    """Run one bounded cleanup batch in its own short-lived transaction."""
    started_at = monotonic()
    db = SessionLocal()
    try:
        deleted = cleanup_expired_route_states(db, limit=limit)
        db.commit()
        logger.info(
            "route_state_cleanup_completed deleted=%s limit=%s duration_ms=%s",
            deleted,
            limit,
            round((monotonic() - started_at) * 1000),
        )
        return deleted
    except Exception:
        db.rollback()
        logger.exception(
            "route_state_cleanup_failed limit=%s duration_ms=%s",
            limit,
            round((monotonic() - started_at) * 1000),
        )
        raise
    finally:
        db.close()
