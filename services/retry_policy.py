"""CITYGO-318: reusable, generic retry/backoff engine.

This module has NO knowledge of OSM, HTTP, Overpass, or any other
external provider. It takes a callable to execute and a caller-supplied
`is_retryable(exception) -> bool` predicate; everything provider-specific
lives in the caller (see services/osm_fetch_retry.py for the OSM-specific
configuration of this engine — that module decides WHAT is retryable,
this module only decides HOW MANY times and HOW LONG to wait).

Dark launch: nothing in this module is imported by any current import
entrypoint. It is a standalone, independently testable component.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class RetryOutcomeKind(str, Enum):
    SUCCESS_NO_RETRY = "success_no_retry"
    SUCCESS_AFTER_RETRY = "success_after_retry"
    PERMANENT_FAILURE = "permanent_failure"
    RETRY_BUDGET_EXHAUSTED = "retry_budget_exhausted"


class RetryPolicyError(ValueError):
    """Raised for invalid RetryConfig — fail closed on misconfiguration."""


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    multiplier: float = 2.0
    jitter: bool = False
    # jitter_ratio: fraction of the computed delay that may be randomly
    # added/subtracted when jitter=True, e.g. 0.1 = +/-10%.
    jitter_ratio: float = 0.1
    timeout_seconds: float | None = None

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise RetryPolicyError(f"max_attempts must be >= 1, got {self.max_attempts!r}")
        if self.initial_delay_seconds < 0:
            raise RetryPolicyError(f"initial_delay_seconds must be >= 0, got {self.initial_delay_seconds!r}")
        if self.max_delay_seconds < 0:
            raise RetryPolicyError(f"max_delay_seconds must be >= 0, got {self.max_delay_seconds!r}")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise RetryPolicyError(
                f"max_delay_seconds ({self.max_delay_seconds}) must be >= "
                f"initial_delay_seconds ({self.initial_delay_seconds})"
            )
        if self.multiplier < 1.0:
            raise RetryPolicyError(f"multiplier must be >= 1.0, got {self.multiplier!r}")
        if not (0.0 <= self.jitter_ratio <= 1.0):
            raise RetryPolicyError(f"jitter_ratio must be within [0.0, 1.0], got {self.jitter_ratio!r}")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise RetryPolicyError(f"timeout_seconds must be positive when set, got {self.timeout_seconds!r}")


@dataclass(frozen=True)
class RetryAttempt:
    """Truthful diagnostics for exactly one attempt (requirement 5)."""

    attempt_number: int
    elapsed_seconds: float
    succeeded: bool
    retryable: bool
    retry_reason: str | None
    error: str | None
    next_delay_seconds: float | None


@dataclass(frozen=True)
class RetryOutcome(Generic[T]):
    """Truthful diagnostics for the whole call (requirements 4, 5, 6). Never
    fabricates success: `success` reflects exactly what happened, `value`
    is None unless `success` is True, and `final_error` preserves the real
    last exception's string representation when the call did not
    succeed."""

    success: bool
    outcome_kind: RetryOutcomeKind
    value: T | None
    attempts: tuple[RetryAttempt, ...]
    total_elapsed_seconds: float
    final_error: str | None

    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


def compute_backoff_delay(
    *,
    attempt_number: int,
    config: RetryConfig,
    rng: Callable[[], float] | None = None,
) -> float:
    """Pure function: exponential backoff capped at max_delay_seconds, with
    optional jitter. attempt_number is 1-based (the delay BEFORE attempt
    N+1, computed after attempt N failed). rng is injectable (defaults to
    random.random) so jitter is testable without relying on real
    randomness in assertions — tests pass a fixed rng to get a
    deterministic, exact expected value."""
    if attempt_number < 1:
        raise RetryPolicyError(f"attempt_number must be >= 1, got {attempt_number!r}")
    raw_delay = config.initial_delay_seconds * (config.multiplier ** (attempt_number - 1))
    capped_delay = min(raw_delay, config.max_delay_seconds)
    if not config.jitter or capped_delay == 0:
        return capped_delay
    roll = (rng or random.random)()
    # roll in [0, 1) -> jitter factor in [-jitter_ratio, +jitter_ratio]
    jitter_factor = (roll * 2.0 - 1.0) * config.jitter_ratio
    jittered = capped_delay * (1.0 + jitter_factor)
    # Jitter must never push the delay outside [0, max_delay_seconds] —
    # the configured cap is a hard ceiling, not a suggestion.
    return max(0.0, min(jittered, config.max_delay_seconds))


def execute_with_retry(
    fn: Callable[[], T],
    *,
    config: RetryConfig,
    is_retryable: Callable[[BaseException], bool],
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    rng: Callable[[], float] | None = None,
) -> RetryOutcome[T]:
    """Executes `fn` with retry/backoff. Never raises on retry exhaustion or
    a non-retryable failure — always returns a RetryOutcome so the caller
    gets truthful diagnostics either way (fail closed, requirement 4: the
    real error, attempt count, and elapsed time are always preserved).

    `sleep`/`now`/`rng` are injectable purely for deterministic testing —
    production callers use the real time.sleep/time.monotonic/random.random
    defaults.
    """
    started = now()
    attempts: list[RetryAttempt] = []

    for attempt_number in range(1, config.max_attempts + 1):
        attempt_started = now()
        try:
            value = fn()
        except BaseException as exc:  # noqa: BLE001 — classification is delegated to is_retryable
            elapsed = now() - attempt_started
            retryable = is_retryable(exc)
            is_last_attempt = attempt_number >= config.max_attempts
            next_delay = None if (not retryable or is_last_attempt) else compute_backoff_delay(
                attempt_number=attempt_number, config=config, rng=rng
            )
            attempts.append(
                RetryAttempt(
                    attempt_number=attempt_number,
                    elapsed_seconds=elapsed,
                    succeeded=False,
                    retryable=retryable,
                    retry_reason=type(exc).__name__ if retryable else None,
                    error=str(exc),
                    next_delay_seconds=next_delay,
                )
            )
            if not retryable:
                return RetryOutcome(
                    success=False,
                    outcome_kind=RetryOutcomeKind.PERMANENT_FAILURE,
                    value=None,
                    attempts=tuple(attempts),
                    total_elapsed_seconds=now() - started,
                    final_error=str(exc),
                )
            if is_last_attempt:
                return RetryOutcome(
                    success=False,
                    outcome_kind=RetryOutcomeKind.RETRY_BUDGET_EXHAUSTED,
                    value=None,
                    attempts=tuple(attempts),
                    total_elapsed_seconds=now() - started,
                    final_error=str(exc),
                )
            sleep(next_delay)
            continue
        else:
            elapsed = now() - attempt_started
            attempts.append(
                RetryAttempt(
                    attempt_number=attempt_number,
                    elapsed_seconds=elapsed,
                    succeeded=True,
                    retryable=False,
                    retry_reason=None,
                    error=None,
                    next_delay_seconds=None,
                )
            )
            outcome_kind = RetryOutcomeKind.SUCCESS_NO_RETRY if attempt_number == 1 else RetryOutcomeKind.SUCCESS_AFTER_RETRY
            return RetryOutcome(
                success=True,
                outcome_kind=outcome_kind,
                value=value,
                attempts=tuple(attempts),
                total_elapsed_seconds=now() - started,
                final_error=None,
            )

    # Unreachable: the loop always returns inside its body for
    # max_attempts >= 1 (enforced by RetryConfig.__post_init__).
    raise AssertionError("execute_with_retry loop exited without returning")
