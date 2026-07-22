"""Worker-process terminal outcome contract (not job lifecycle ownership).

Classifies DB terminal statuses into process exit policy without changing
finalize_import_job / runner transitions.
"""

from __future__ import annotations

# a) completed successfully
TERMINAL_SUCCESS_STATUSES = frozenset({"success", "success_with_warnings"})
# b) completed with partial result (still a completed worker run)
TERMINAL_PARTIAL_STATUSES = frozenset({"partial_success"})
# c) ended unsuccessfully
TERMINAL_FAILURE_STATUSES = frozenset({"failed"})
# d) externally stopped (stall sweep / admin cancel)
TERMINAL_EXTERNAL_STOP_STATUSES = frozenset({"stalled", "cancelled"})

ALL_TERMINAL_JOB_STATUSES = (
    TERMINAL_SUCCESS_STATUSES
    | TERMINAL_PARTIAL_STATUSES
    | TERMINAL_FAILURE_STATUSES
    | TERMINAL_EXTERNAL_STOP_STATUSES
)

OUTCOME_SUCCESS = "success"
OUTCOME_PARTIAL = "partial"
OUTCOME_FAILED = "failed"
OUTCOME_EXTERNAL_STOP = "external_stop"
OUTCOME_INCOMPLETE = "incomplete"


def classify_terminal_status(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized in TERMINAL_SUCCESS_STATUSES:
        return OUTCOME_SUCCESS
    if normalized in TERMINAL_PARTIAL_STATUSES:
        return OUTCOME_PARTIAL
    if normalized in TERMINAL_FAILURE_STATUSES:
        return OUTCOME_FAILED
    if normalized in TERMINAL_EXTERNAL_STOP_STATUSES:
        return OUTCOME_EXTERNAL_STOP
    return OUTCOME_INCOMPLETE


def is_terminal_job_status(status: str | None) -> bool:
    return classify_terminal_status(status) != OUTCOME_INCOMPLETE


def process_success_exit(outcome_kind: str) -> bool:
    """Exit 0 only for completed imports (full or partial). Never for
    failed / external-stop / incomplete — stalled/cancelled must not look
    like a successful import run."""
    return outcome_kind in {OUTCOME_SUCCESS, OUTCOME_PARTIAL}


def skip_reason_for_outcome(outcome_kind: str, *, status: str | None) -> str | None:
    if outcome_kind == OUTCOME_FAILED:
        return "job_terminal_failed"
    if outcome_kind == OUTCOME_EXTERNAL_STOP:
        return f"job_externally_stopped:{status}"
    if outcome_kind == OUTCOME_INCOMPLETE:
        return "job_finalize_did_not_reach_terminal_status"
    return None
