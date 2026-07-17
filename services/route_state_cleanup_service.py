from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

ROUTE_STATE_CLEANUP_BATCH_SIZE = 100
ROUTE_STATE_CLEANUP_MAX_BATCH_SIZE = 10_000


def cleanup_expired_route_states(
    db: Session,
    *,
    cutoff: datetime | None = None,
    limit: int = ROUTE_STATE_CLEANUP_BATCH_SIZE,
) -> int:
    """Delete a bounded batch of states that are still expired at delete time.

    This service owns only the cleanup statement. The caller owns the short-lived
    transaction and commit/rollback. It must never be called from route build,
    registration, verification, or mutation request transactions.
    """
    batch_limit = max(1, min(int(limit), ROUTE_STATE_CLEANUP_MAX_BATCH_SIZE))
    dialect = db.get_bind().dialect.name
    params: dict[str, object] = {"limit": batch_limit}

    if cutoff is None:
        cutoff_expression = "clock_timestamp()" if dialect == "postgresql" else "CURRENT_TIMESTAMP"
    else:
        cutoff_expression = ":cutoff"
        params["cutoff"] = cutoff

    if dialect == "postgresql":
        statement = text(
            f"""
            WITH expired AS (
                SELECT route_id
                FROM user_route_state_registry
                WHERE expires_at <= {cutoff_expression}
                ORDER BY expires_at, route_id
                FOR UPDATE SKIP LOCKED
                LIMIT :limit
            )
            DELETE FROM user_route_state_registry AS registry
            USING expired
            WHERE registry.route_id = expired.route_id
              AND registry.expires_at <= {cutoff_expression}
            RETURNING registry.route_id
            """
        )
        result = db.execute(statement, params)
        return len(result.fetchall())

    if dialect == "sqlite":
        statement = text(
            f"""
            DELETE FROM user_route_state_registry
            WHERE route_id IN (
                SELECT route_id
                FROM user_route_state_registry
                WHERE expires_at <= {cutoff_expression}
                ORDER BY expires_at, route_id
                LIMIT :limit
            )
              AND expires_at <= {cutoff_expression}
            """
        )
        result = db.execute(statement, params, execution_options={"synchronize_session": False})
        return max(0, int(result.rowcount or 0))

    raise RuntimeError(f"Unsupported route-state cleanup database dialect: {dialect}")
