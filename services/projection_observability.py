"""Structured Stage 5 rollout events using the existing logging stack."""

import json
import logging

logger = logging.getLogger("citygo.public_read_projections")
logger.setLevel(logging.INFO)


def log_projection_read(
    *, read_path: str, projection_type: str, city_id: int | None,
    uses_projection: bool, latency_ms: int, reason: str = "projection_ready",
    source_version: int | None = None, projection_version: int | None = None,
) -> None:
    logger.info(json.dumps({
        "event": "projection_read",
        "read_path": read_path,
        "projection_type": projection_type,
        "city_id": city_id,
        "path": "projection" if uses_projection else "legacy",
        "reason": reason,
        "source_version": source_version,
        "projection_version": projection_version,
        "latency_ms": latency_ms,
    }, sort_keys=True))


def log_projection_unavailable(*, read_path: str, reason: str) -> None:
    logger.warning(json.dumps({
        "event": "public_read_projection_unavailable",
        "read_path": read_path,
        "reason": reason,
    }, sort_keys=True))


def log_rebuild_result(*, projection_type: str, city_id: int | None, status: str, reason: str | None = None) -> None:
    payload = {"event": "projection_rebuild", "projection_type": projection_type,
               "city_id": city_id, "status": status, "reason": reason}
    (logger.warning if status == "failed" else logger.info)(json.dumps(payload, sort_keys=True))
