"""CITYGO-318: OSM-specific retry configuration (services/osm_fetch_retry.py).

Covers HTTP status classification, connection/DNS/timeout classification,
non-retryable classification, the dark-launch/no-current-callers proof,
and end-to-end integration with the generic engine using OSM-shaped
exceptions.
"""

from __future__ import annotations

import json
import socket
import urllib.error

from services.osm_fetch_retry import (
    DEFAULT_OSM_RETRY_CONFIG,
    RETRYABLE_HTTP_STATUS_CODES,
    fetch_osm_objects_with_retry,
    is_osm_transient_error,
)
from services.retry_policy import RetryConfig, RetryOutcomeKind


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url="https://overpass-api.de/api/interpreter", code=code, msg="err", hdrs=None, fp=None)


# --- transient HTTP status classification ---


def test_retryable_status_codes_classified_transient_new():
    for code in (429, 500, 502, 503, 504):
        assert is_osm_transient_error(_http_error(code)) is True


def test_non_retryable_status_codes_classified_permanent_new():
    for code in (400, 401, 403, 404, 405, 422):
        assert is_osm_transient_error(_http_error(code)) is False


def test_retryable_status_codes_constant_matches_requirement_new():
    assert RETRYABLE_HTTP_STATUS_CODES == frozenset({429, 500, 502, 503, 504})


# --- connection/timeout/dns classification ---


def test_connection_reset_is_transient_new():
    assert is_osm_transient_error(ConnectionResetError("connection reset by peer")) is True


def test_timeout_error_is_transient_new():
    assert is_osm_transient_error(TimeoutError("timed out")) is True


def test_socket_timeout_is_transient_new():
    assert is_osm_transient_error(socket.timeout("timed out")) is True


def test_dns_failure_is_transient_new():
    assert is_osm_transient_error(socket.gaierror("Name or service not known")) is True


def test_urlerror_wrapping_dns_failure_is_transient_new():
    assert is_osm_transient_error(urllib.error.URLError(socket.gaierror("dns"))) is True


def test_urlerror_wrapping_os_error_is_transient_new():
    assert is_osm_transient_error(urllib.error.URLError(OSError("network unreachable"))) is True


# --- non-retryable classification ---


def test_urlerror_with_non_network_reason_is_not_transient_new():
    assert is_osm_transient_error(urllib.error.URLError("malformed url")) is False


def test_json_decode_error_is_not_transient_new():
    try:
        json.loads("not json")
    except json.JSONDecodeError as exc:
        assert is_osm_transient_error(exc) is False
    else:
        raise AssertionError("expected JSONDecodeError")


def test_plain_value_error_is_not_transient_new():
    assert is_osm_transient_error(ValueError("unsupported profile")) is False


def test_unrelated_exception_type_is_not_transient_new():
    assert is_osm_transient_error(RuntimeError("unexpected")) is False


# --- integration with the generic engine ---


def test_fetch_with_retry_succeeds_after_transient_failures_new():
    attempts = []

    def flaky_fetch():
        attempts.append(1)
        if len(attempts) < 3:
            raise _http_error(503)
        return [{"id": 1, "type": "node"}]

    outcome = fetch_osm_objects_with_retry(flaky_fetch, config=RetryConfig(max_attempts=5, initial_delay_seconds=0.001, jitter=False))

    assert outcome.success is True
    assert outcome.outcome_kind == RetryOutcomeKind.SUCCESS_AFTER_RETRY
    assert outcome.value == [{"id": 1, "type": "node"}]
    assert outcome.attempt_count == 3


def test_fetch_with_retry_fails_closed_on_non_retryable_error_new():
    attempts = []

    def bad_profile_fetch():
        attempts.append(1)
        raise ValueError("Unsupported OSM import profile: bogus")

    outcome = fetch_osm_objects_with_retry(bad_profile_fetch, config=RetryConfig(max_attempts=5, initial_delay_seconds=0.001))

    assert outcome.success is False
    assert outcome.outcome_kind == RetryOutcomeKind.PERMANENT_FAILURE
    assert len(attempts) == 1


def test_fetch_with_retry_exhausts_budget_and_preserves_error_new():
    def always_rate_limited():
        raise _http_error(429)

    outcome = fetch_osm_objects_with_retry(always_rate_limited, config=RetryConfig(max_attempts=3, initial_delay_seconds=0.001))

    assert outcome.success is False
    assert outcome.outcome_kind == RetryOutcomeKind.RETRY_BUDGET_EXHAUSTED
    assert outcome.attempt_count == 3
    assert outcome.value is None


def test_fetch_with_retry_uses_default_config_when_none_provided_new():
    def ok():
        return []

    outcome = fetch_osm_objects_with_retry(ok)

    assert outcome.success is True
    assert outcome.attempt_count == 1


def test_default_osm_retry_config_is_sane_new():
    assert DEFAULT_OSM_RETRY_CONFIG.max_attempts >= 1
    assert DEFAULT_OSM_RETRY_CONFIG.timeout_seconds is not None


# --- no current production caller (dark launch) ---


def test_osm_fetch_retry_has_no_current_import_callers_new():
    """CITYGO-319 explicitly wires fetch_osm_objects_with_retry into
    data/scripts/import_city_osm.py's tiled apply path, so that file is
    excluded from this dark-launch guard. Every other entrypoint must
    still not reference the retry engine."""
    from pathlib import Path

    entrypoints = (
        Path("data/scripts/import_city_osm_v2.py"),
        Path("data/scripts/run_due_import_jobs.py"),
        Path("services/admin_city_import_runner.py"),
        Path("services/admin_city_import_job_service.py"),
        Path("services/admin_city_import_tasks.py"),
        Path("services/import_pipeline/runner.py"),
    )
    for path in entrypoints:
        assert path.exists(), f"expected entrypoint file missing: {path}"
        source = path.read_text(encoding="utf-8")
        assert "osm_fetch_retry" not in source, f"{path} must not reference osm_fetch_retry yet"
        assert "retry_policy" not in source, f"{path} must not reference retry_policy yet"
        assert "fetch_osm_objects_with_retry" not in source, f"{path} must not call fetch_osm_objects_with_retry yet"


def test_fetch_osm_objects_function_in_production_is_unmodified_and_has_no_retry_loop_new():
    """Requirement 8: existing production import behavior must remain
    unchanged. _fetch_osm_objects must still be exactly one urlopen call —
    no retry loop was added to it."""
    from pathlib import Path

    source = Path("data/scripts/import_city_osm.py").read_text(encoding="utf-8")
    body = source.split("def _fetch_osm_objects(", 1)[1].split("\ndef _normalize_osm_object(", 1)[0]

    assert body.count("urllib.request.urlopen(") == 1
    assert "for attempt" not in body
    assert "while" not in body
    assert "retry" not in body.lower()
