"""CITYGO-318: generic retry/backoff engine (services/retry_policy.py).

All tests inject deterministic sleep/now/rng callables so timing/jitter
assertions are exact, never flaky, and never actually sleep in real time.
"""

from __future__ import annotations

import pytest

from services.retry_policy import (
    RetryConfig,
    RetryOutcomeKind,
    RetryPolicyError,
    compute_backoff_delay,
    execute_with_retry,
)


def _fake_clock(start: float = 0.0, step: float = 0.05):
    """Deterministic now() that advances by `step` seconds on every call."""
    state = {"t": start}

    def _now() -> float:
        state["t"] += step
        return state["t"]

    return _now


# --- immediate success ---


def test_immediate_success_no_retry_new():
    calls = []

    def fn():
        calls.append(1)
        return "value"

    outcome = execute_with_retry(fn, config=RetryConfig(max_attempts=3), is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())

    assert outcome.success is True
    assert outcome.outcome_kind == RetryOutcomeKind.SUCCESS_NO_RETRY
    assert outcome.value == "value"
    assert outcome.attempt_count == 1
    assert len(calls) == 1
    assert outcome.final_error is None


# --- success after one retry ---


def test_success_after_one_retry_new():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 2:
            raise ConnectionResetError("reset")
        return "recovered"

    sleeps = []
    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=3, initial_delay_seconds=1.0), is_retryable=lambda e: True,
        sleep=lambda s: sleeps.append(s), now=_fake_clock(),
    )

    assert outcome.success is True
    assert outcome.outcome_kind == RetryOutcomeKind.SUCCESS_AFTER_RETRY
    assert outcome.value == "recovered"
    assert outcome.attempt_count == 2
    assert sleeps == [1.0]


# --- success after several retries ---


def test_success_after_several_retries_new():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 4:
            raise TimeoutError("t")
        return "finally"

    sleeps = []
    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=5, initial_delay_seconds=0.5, multiplier=2.0), is_retryable=lambda e: True,
        sleep=lambda s: sleeps.append(s), now=_fake_clock(),
    )

    assert outcome.success is True
    assert outcome.attempt_count == 4
    assert sleeps == [0.5, 1.0, 2.0]


# --- retry budget exhausted ---


def test_retry_budget_exhausted_new():
    def fn():
        raise TimeoutError("always times out")

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=3, initial_delay_seconds=0.1), is_retryable=lambda e: True,
        sleep=lambda s: None, now=_fake_clock(),
    )

    assert outcome.success is False
    assert outcome.outcome_kind == RetryOutcomeKind.RETRY_BUDGET_EXHAUSTED
    assert outcome.value is None
    assert outcome.attempt_count == 3
    assert outcome.final_error == "always times out"


def test_retry_budget_exhausted_preserves_real_error_never_fabricates_success_new():
    def fn():
        raise TimeoutError("provider unreachable")

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=2, initial_delay_seconds=0.01), is_retryable=lambda e: True,
        sleep=lambda s: None, now=_fake_clock(),
    )

    assert outcome.success is False
    assert "provider unreachable" in outcome.final_error
    assert outcome.value is None
    assert all(not attempt.succeeded for attempt in outcome.attempts)


# --- non-retryable error ---


def test_non_retryable_error_fails_immediately_new():
    attempts = []

    def fn():
        attempts.append(1)
        raise ValueError("bad json")

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=5), is_retryable=lambda e: False,
        sleep=lambda s: None, now=_fake_clock(),
    )

    assert outcome.success is False
    assert outcome.outcome_kind == RetryOutcomeKind.PERMANENT_FAILURE
    assert outcome.attempt_count == 1
    assert len(attempts) == 1


def test_non_retryable_error_does_not_sleep_new():
    sleeps = []

    def fn():
        raise ValueError("malformed query")

    execute_with_retry(
        fn, config=RetryConfig(max_attempts=5), is_retryable=lambda e: False,
        sleep=lambda s: sleeps.append(s), now=_fake_clock(),
    )

    assert sleeps == []


# --- timeout (per-attempt config value is preserved, not enforced by this engine directly) ---


def test_timeout_seconds_config_accepted_and_preserved_new():
    """The engine does not itself impose a wall-clock timeout on `fn` (the
    caller's fn is responsible for its own timeout, e.g. urlopen(timeout=)),
    but the configured value must be preserved/accepted, not silently
    dropped or rejected."""
    config = RetryConfig(max_attempts=2, timeout_seconds=45.0)
    assert config.timeout_seconds == 45.0


def test_timeout_error_is_retried_like_any_other_retryable_exception_new():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 2:
            raise TimeoutError("request timed out")
        return "ok"

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=3, initial_delay_seconds=0.01), is_retryable=lambda e: isinstance(e, TimeoutError),
        sleep=lambda s: None, now=_fake_clock(),
    )

    assert outcome.success is True
    assert outcome.attempt_count == 2


# --- exponential delay calculation ---


def test_exponential_delay_calculation_no_jitter_new():
    config = RetryConfig(initial_delay_seconds=1.0, max_delay_seconds=100.0, multiplier=2.0, jitter=False)

    delays = [compute_backoff_delay(attempt_number=n, config=config) for n in range(1, 6)]

    assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]


def test_exponential_delay_capped_at_max_delay_new():
    config = RetryConfig(initial_delay_seconds=1.0, max_delay_seconds=5.0, multiplier=2.0, jitter=False)

    delays = [compute_backoff_delay(attempt_number=n, config=config) for n in range(1, 6)]

    assert delays == [1.0, 2.0, 4.0, 5.0, 5.0]


def test_exponential_delay_with_multiplier_one_is_constant_new():
    config = RetryConfig(initial_delay_seconds=2.0, max_delay_seconds=100.0, multiplier=1.0, jitter=False)

    delays = [compute_backoff_delay(attempt_number=n, config=config) for n in range(1, 4)]

    assert delays == [2.0, 2.0, 2.0]


def test_negative_attempt_number_rejected_new():
    config = RetryConfig()
    with pytest.raises(RetryPolicyError):
        compute_backoff_delay(attempt_number=0, config=config)


# --- jitter boundaries ---


def test_jitter_stays_within_configured_ratio_new():
    config = RetryConfig(initial_delay_seconds=10.0, max_delay_seconds=100.0, multiplier=1.0, jitter=True, jitter_ratio=0.2)

    low = compute_backoff_delay(attempt_number=1, config=config, rng=lambda: 0.0)
    mid = compute_backoff_delay(attempt_number=1, config=config, rng=lambda: 0.5)
    high = compute_backoff_delay(attempt_number=1, config=config, rng=lambda: 1.0)

    assert low == 8.0  # 10 * (1 - 0.2)
    assert mid == 10.0  # 10 * (1 + 0.0)
    assert high == 12.0  # 10 * (1 + 0.2)


def test_jitter_never_exceeds_max_delay_new():
    config = RetryConfig(initial_delay_seconds=9.5, max_delay_seconds=10.0, multiplier=1.0, jitter=True, jitter_ratio=0.5)

    high = compute_backoff_delay(attempt_number=1, config=config, rng=lambda: 1.0)

    assert high == 10.0


def test_jitter_never_goes_negative_new():
    config = RetryConfig(initial_delay_seconds=1.0, max_delay_seconds=10.0, multiplier=1.0, jitter=True, jitter_ratio=1.0)

    low = compute_backoff_delay(attempt_number=1, config=config, rng=lambda: 0.0)

    assert low == 0.0


# --- deterministic behavior with jitter disabled ---


def test_deterministic_delays_with_jitter_disabled_across_repeated_calls_new():
    config = RetryConfig(initial_delay_seconds=1.0, max_delay_seconds=50.0, multiplier=3.0, jitter=False)

    run1 = [compute_backoff_delay(attempt_number=n, config=config) for n in range(1, 5)]
    run2 = [compute_backoff_delay(attempt_number=n, config=config) for n in range(1, 5)]

    assert run1 == run2 == [1.0, 3.0, 9.0, 27.0]


def test_full_retry_sequence_deterministic_without_jitter_new():
    def make_fn():
        attempts = []

        def fn():
            attempts.append(1)
            if len(attempts) < 3:
                raise TimeoutError("t")
            return "done"

        return fn

    config = RetryConfig(max_attempts=4, initial_delay_seconds=0.25, multiplier=2.0, jitter=False)
    outcome1 = execute_with_retry(make_fn(), config=config, is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())
    outcome2 = execute_with_retry(make_fn(), config=config, is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())

    assert [a.next_delay_seconds for a in outcome1.attempts] == [a.next_delay_seconds for a in outcome2.attempts]
    assert outcome1.attempt_count == outcome2.attempt_count == 3


# --- diagnostics correctness ---


def test_diagnostics_record_attempt_number_elapsed_reason_next_delay_new():
    attempts = []

    def fn():
        attempts.append(1)
        if len(attempts) < 2:
            raise ConnectionResetError("reset")
        return "ok"

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=3, initial_delay_seconds=2.0), is_retryable=lambda e: True,
        sleep=lambda s: None, now=_fake_clock(step=0.1),
    )

    first, second = outcome.attempts
    assert first.attempt_number == 1
    assert first.succeeded is False
    assert first.retryable is True
    assert first.retry_reason == "ConnectionResetError"
    assert first.error == "reset"
    assert first.next_delay_seconds == 2.0
    assert first.elapsed_seconds > 0

    assert second.attempt_number == 2
    assert second.succeeded is True
    assert second.next_delay_seconds is None
    assert second.error is None


def test_diagnostics_total_elapsed_time_reflects_all_attempts_new():
    def fn():
        raise TimeoutError("t")

    outcome = execute_with_retry(
        fn, config=RetryConfig(max_attempts=3, initial_delay_seconds=0.01), is_retryable=lambda e: True,
        sleep=lambda s: None, now=_fake_clock(step=0.1),
    )

    assert outcome.total_elapsed_seconds > 0
    assert outcome.attempt_count == 3


# --- diagnostics distinguish the 4 outcome kinds (requirement 6) ---


def test_outcome_kinds_are_distinguishable_new():
    def ok_fn():
        return "x"

    def ok_after_retry():
        state = {"n": 0}

        def _inner():
            state["n"] += 1
            if state["n"] < 2:
                raise TimeoutError("t")
            return "x"

        return _inner

    def permanent_fail():
        raise ValueError("bad")

    def exhausted():
        raise TimeoutError("t")

    outcome_no_retry = execute_with_retry(ok_fn, config=RetryConfig(max_attempts=3), is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())
    outcome_after_retry = execute_with_retry(ok_after_retry(), config=RetryConfig(max_attempts=3, initial_delay_seconds=0.01), is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())
    outcome_permanent = execute_with_retry(permanent_fail, config=RetryConfig(max_attempts=3), is_retryable=lambda e: False, sleep=lambda s: None, now=_fake_clock())
    outcome_exhausted = execute_with_retry(exhausted, config=RetryConfig(max_attempts=2, initial_delay_seconds=0.01), is_retryable=lambda e: True, sleep=lambda s: None, now=_fake_clock())

    kinds = {
        outcome_no_retry.outcome_kind,
        outcome_after_retry.outcome_kind,
        outcome_permanent.outcome_kind,
        outcome_exhausted.outcome_kind,
    }
    assert kinds == {
        RetryOutcomeKind.SUCCESS_NO_RETRY,
        RetryOutcomeKind.SUCCESS_AFTER_RETRY,
        RetryOutcomeKind.PERMANENT_FAILURE,
        RetryOutcomeKind.RETRY_BUDGET_EXHAUSTED,
    }


# --- fail-closed config validation ---


def test_invalid_max_attempts_fails_closed_new():
    with pytest.raises(RetryPolicyError):
        RetryConfig(max_attempts=0)


def test_max_delay_less_than_initial_delay_fails_closed_new():
    with pytest.raises(RetryPolicyError):
        RetryConfig(initial_delay_seconds=10.0, max_delay_seconds=5.0)


def test_multiplier_below_one_fails_closed_new():
    with pytest.raises(RetryPolicyError):
        RetryConfig(multiplier=0.5)


def test_jitter_ratio_out_of_range_fails_closed_new():
    with pytest.raises(RetryPolicyError):
        RetryConfig(jitter_ratio=1.5)


def test_negative_timeout_fails_closed_new():
    with pytest.raises(RetryPolicyError):
        RetryConfig(timeout_seconds=-1.0)


# --- reusability: no OSM/HTTP-specific logic inside the engine ---


def test_engine_module_has_no_osm_or_http_specific_logic_new():
    """The module docstring may legitimately mention OSM/Overpass as
    explanatory context about WHY the engine exists — this checks the
    actual parsed AST (imports and code statements), not the module's
    docstring/comment prose."""
    import ast
    import inspect

    import services.retry_policy as module

    tree = ast.parse(inspect.getsource(module))
    imported_names = sorted(
        {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        | {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    )
    assert imported_names == ["__future__", "dataclasses", "enum", "random", "time", "typing"]

    # No hardcoded HTTP status codes or provider-specific literals anywhere
    # in the module's string/constant literals.
    literals = [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int))
    ]
    for forbidden in (429, 500, 502, 503, 504, "Overpass", "overpass", "OSM"):
        assert forbidden not in literals, f"retry_policy.py must stay generic, found provider-specific literal: {forbidden!r}"
