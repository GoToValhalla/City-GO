from __future__ import annotations

import logging
from time import monotonic

logger = logging.getLogger(__name__)


def request_started() -> float:
    return monotonic()


def log_backend_success(
    operation: str,
    base_url: str,
    started: float,
    status_code: int | None = None,
) -> None:
    logger.info(
        "telegram_backend_request ok operation=%s base_url=%s status=%s duration_ms=%s",
        operation,
        base_url,
        status_code or "-",
        _duration_ms(started),
    )


def log_backend_error(
    operation: str,
    base_url: str,
    started: float,
    error: object,
) -> None:
    logger.warning(
        "telegram_backend_request error operation=%s base_url=%s error_type=%s duration_ms=%s",
        operation,
        base_url,
        type(error).__name__,
        _duration_ms(started),
    )


def _duration_ms(started: float) -> int:
    return int((monotonic() - started) * 1000)
