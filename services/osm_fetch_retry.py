"""CITYGO-318: OSM-specific retry configuration for services/retry_policy.py.

This module contains ALL of the OSM/HTTP-specific knowledge (which status
codes and exception types are transient) — the generic engine in
services/retry_policy.py has none. This module only classifies errors and
calls the generic engine; it does not implement retry/backoff logic itself.

Dark launch: fetch_osm_objects_with_retry() is a standalone function, not
called by data/scripts/import_city_osm.py or any other current import
entrypoint. Existing production OSM fetch behavior
(data/scripts/import_city_osm.py::_fetch_osm_objects, a single
urllib.request.urlopen call with no retry) is completely unchanged.
"""

from __future__ import annotations

import socket
import urllib.error
from typing import Any, Callable

from services.retry_policy import RetryConfig, RetryOutcome, execute_with_retry

# HTTP status codes considered transient for an Overpass-style provider —
# rate limiting and server-side/gateway errors that are expected to
# self-resolve on retry. Anything else (4xx other than 429, malformed
# request, auth/config errors) is NOT in this set and must not be retried.
RETRYABLE_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

DEFAULT_OSM_RETRY_CONFIG = RetryConfig(
    max_attempts=4,
    initial_delay_seconds=1.0,
    max_delay_seconds=20.0,
    multiplier=2.0,
    jitter=True,
    jitter_ratio=0.2,
    timeout_seconds=60.0,
)


def is_osm_transient_error(exc: BaseException) -> bool:
    """Classifies a single exception raised while fetching from an
    Overpass-style OSM provider as retryable (transient) or not.

    Retryable: HTTP 429/500/502/503/504, connection reset, connection
    timeout, and temporary DNS/network failures (urllib.error.URLError
    wrapping a socket.gaierror or a generic OSError/socket.timeout).

    NOT retryable: any other HTTP status (e.g. 400/401/403/404 — invalid
    request, authentication/configuration errors), JSON/parsing errors
    (ValueError, json.JSONDecodeError, which is a ValueError subclass),
    and any other deterministic validation failure — retrying these would
    just reproduce the same failure and waste the retry budget.
    """
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in RETRYABLE_HTTP_STATUS_CODES
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, ConnectionResetError):
        return True
    if isinstance(exc, socket.gaierror):
        return True
    if isinstance(exc, urllib.error.URLError):
        # URLError.reason is often a nested OSError/socket.gaierror for DNS
        # and connection-level failures; a bare string reason (e.g. a
        # malformed URL) is not a transient network condition.
        return isinstance(exc.reason, (OSError, socket.gaierror, TimeoutError))
    if isinstance(exc, ValueError):
        # Covers json.JSONDecodeError and any other parsing/validation
        # failure — these are deterministic, not transient.
        return False
    return False


def fetch_osm_objects_with_retry(
    fetch_fn: Callable[[], list[dict[str, Any]]],
    *,
    config: RetryConfig | None = None,
) -> RetryOutcome[list[dict[str, Any]]]:
    """Runs `fetch_fn` (a zero-arg callable performing one Overpass HTTP
    call, e.g. a thin wrapper around data/scripts/import_city_osm.py's
    existing request-building/urlopen logic) through the generic retry
    engine with OSM-specific transient-error classification.

    Not called by any current import code — a future task decides whether
    and how to wire this into data/scripts/import_city_osm.py.
    """
    return execute_with_retry(
        fetch_fn,
        config=config or DEFAULT_OSM_RETRY_CONFIG,
        is_retryable=is_osm_transient_error,
    )
