"""Persistent import worker loop with bounded health and shutdown behavior."""

from __future__ import annotations

import json
import os
import signal
import sys
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_tasks import import_queue_summary, run_queued_import_jobs
from services.import_worker_thresholds import log_effective_thresholds

_STOP = False

RUN_MODE_SAFE_ONE_JOB = "safe_one_job"
RUN_MODE_DRY_RUN = "dry_run"
RUN_MODE_DIAGNOSTICS_ONLY = "diagnostics_only"

TERMINAL_JOB_STATUSES = frozenset({"success", "success_with_warnings", "partial_success", "failed"})


@dataclass
class WorkerOutcome:
    requested_city_slug: str | None
    matched_job_id: int | None = None
    claimed: bool = False
    processed: bool = False
    terminal_status: str | None = None
    skip_reason: str | None = None
    elapsed_seconds: float = 0.0
    exit_code: int = 0
    # Diagnostic fields for a claimed-but-non-terminal job, sourced from the
    # runner's own freshly reloaded row (see run_queued_import_jobs) -- never
    # invented here. Populated whenever a job was claimed, regardless of
    # whether it ultimately reached a terminal status.
    claimed_by: str | None = None
    expected_claimed_by: str | None = None
    finished_at: str | None = None
    _started_at: float = field(default_factory=time.monotonic, repr=False, compare=False)

    def finalize(self, *, exit_code: int) -> "WorkerOutcome":
        self.elapsed_seconds = round(time.monotonic() - self._started_at, 3)
        self.exit_code = exit_code
        return self

    def as_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("_started_at", None)
        return payload


class WorkerStopRequested(RuntimeError):
    """Raised from SIGTERM/SIGINT so an active job reaches failure handling."""


def _stop(signum, _frame) -> None:
    global _STOP
    _STOP = True
    raise WorkerStopRequested(f"import-worker stop requested by signal {signum}")


def backend_is_healthy(health_url: str, *, timeout_seconds: float = 5.0) -> bool:
    """Deterministic, single-request backend readiness check."""
    if not health_url:
        return True
    try:
        with urllib.request.urlopen(health_url, timeout=timeout_seconds) as response:  # noqa: S310
            return 200 <= response.status < 300
    except Exception:  # noqa: BLE001
        return False


def run_worker_loop(
    *,
    limit: int,
    sleep_seconds: int,
    actor_id: str = "import-worker",
    max_iterations: int | None = None,
    health_url: str = "",
    max_runtime_seconds: int | None = None,
    city_slug: str | None = None,
    dry_run: bool = False,
    outcome: WorkerOutcome | None = None,
) -> WorkerOutcome:
    """Runs the claim loop and returns the structured outcome. If `outcome`
    is not supplied, a fresh one is created and returned."""
    outcome = outcome or WorkerOutcome(requested_city_slug=city_slug)
    consecutive_failures = 0
    iteration = 0
    started_at = time.monotonic()
    while not _STOP and (max_iterations is None or iteration < max_iterations):
        if max_runtime_seconds is not None and (time.monotonic() - started_at) >= max_runtime_seconds:
            print(f"import_worker_max_runtime_reached seconds={max_runtime_seconds}", file=sys.stderr, flush=True)
            send_admin_alert(
                title="Import-worker остановлен по таймауту",
                message=f"Import-worker завершает работу: превышен лимит времени выполнения ({max_runtime_seconds} с).",
                level="info",
                details={"status": "max_runtime_reached", "max_runtime_seconds": max_runtime_seconds},
            )
            if outcome.terminal_status not in TERMINAL_JOB_STATUSES:
                # Runtime expired without the claimed job (if any) ever
                # reaching a terminal status: this is a stall, not success.
                outcome.skip_reason = outcome.skip_reason or "max_runtime_without_terminal_progress"
            break
        if not backend_is_healthy(health_url):
            print(f"import_worker_backend_unhealthy url={health_url}", file=sys.stderr, flush=True)
            send_admin_alert(
                title="Import-worker остановлен: backend недоступен",
                message=f"Import-worker прекращает обработку: backend health check ({health_url}) не прошёл.",
                level="error",
                details={"status": "backend_unhealthy", "health_url": health_url},
            )
            outcome.skip_reason = outcome.skip_reason or "backend_unhealthy"
            break
        iteration += 1
        try:
            result = run_queued_import_jobs(actor_id=actor_id, limit=limit, city_slug=city_slug, dry_run=dry_run)
            if dry_run:
                would_process = result.get("would_process") or []
                print(f"import_worker_dry_run would_process={would_process}", flush=True)
                if would_process:
                    first = would_process[0]
                    outcome.matched_job_id = int(first["job_id"])
                    outcome.claimed = True
            else:
                claimed_jobs = result.get("claimed_jobs") or []
                if claimed_jobs:
                    first = claimed_jobs[0]
                    outcome.matched_job_id = int(first["job_id"])
                    outcome.claimed = True
                    outcome.terminal_status = str(first.get("terminal_status") or None)
                    outcome.processed = outcome.terminal_status in TERMINAL_JOB_STATUSES
                    outcome.claimed_by = first.get("claimed_by")
                    outcome.expected_claimed_by = first.get("expected_claimed_by")
                    outcome.finished_at = first.get("finished_at")
                elif not outcome.claimed:
                    outcome.skip_reason = outcome.skip_reason or "no_queued_job_matched"
            if consecutive_failures:
                send_admin_alert(
                    title="Import-worker восстановлен",
                    message=f"Import-worker снова работает после {consecutive_failures} ошибок подряд.",
                    level="info",
                    details={"status": "recovered", "previous_failures": consecutive_failures, "queue": result.get("queue")},
                )
            consecutive_failures = 0
        except WorkerStopRequested as exc:
            print(str(exc), file=sys.stderr, flush=True)
            send_admin_alert(
                title="Import-worker остановлен безопасно",
                message=str(exc),
                level="error",
                details={"status": "stop_requested"},
            )
            outcome.skip_reason = outcome.skip_reason or "stop_requested"
            break
        except Exception as exc:  # noqa: BLE001
            consecutive_failures += 1
            if consecutive_failures in {1, 3} or consecutive_failures % 10 == 0:
                send_admin_alert(
                    title="Import worker job failed",
                    message=str(exc)[:1000],
                    level="error",
                    details={"status": "failed", "consecutive_failures": consecutive_failures},
                )
            print(f"import_worker_loop_failed count={consecutive_failures}: {exc}", file=sys.stderr, flush=True)
            outcome.skip_reason = outcome.skip_reason or f"loop_error:{exc}"[:200]
        if not _STOP and (max_iterations is None or iteration < max_iterations):
            time.sleep(sleep_seconds)
    return outcome


def run_diagnostics_only(*, city_slug: str | None = None) -> None:
    """Read-only queue report. Performs no claim, no job execution, no
    mutation of any kind — not even stalled-job marking."""
    with SessionLocal() as db:
        summary = import_queue_summary(db)
    if city_slug:
        summary = {**summary, "city_slug_filter": city_slug}
    print(f"import_worker_diagnostics_only queue={summary}", flush=True)


def _print_outcome(outcome: WorkerOutcome) -> None:
    print(f"import_worker_outcome {json.dumps(outcome.as_dict(), sort_keys=True)}", flush=True)


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    log_effective_thresholds()

    run_mode = os.getenv("IMPORT_WORKER_RUN_MODE", RUN_MODE_SAFE_ONE_JOB).strip() or RUN_MODE_SAFE_ONE_JOB
    city_slug = os.getenv("IMPORT_WORKER_CITY_SLUG", "").strip() or None

    if run_mode == RUN_MODE_DIAGNOSTICS_ONLY:
        run_diagnostics_only(city_slug=city_slug)
        return 0

    if run_mode not in (RUN_MODE_SAFE_ONE_JOB, RUN_MODE_DRY_RUN):
        print(f"import_worker_unknown_run_mode mode={run_mode!r}; falling back to {RUN_MODE_SAFE_ONE_JOB}", file=sys.stderr, flush=True)
        run_mode = RUN_MODE_SAFE_ONE_JOB

    is_dry_run = run_mode == RUN_MODE_DRY_RUN
    # Both safe_one_job and dry_run process at most one iteration/job per
    # run: safe_one_job to bound blast radius on a resource-constrained
    # host, dry_run because it never mutates and one look at the queue is
    # enough to report what would happen. IMPORT_WORKER_BATCH_LIMIT can only
    # lower this floor, never raise it, in either mode.
    configured_limit = max(1, int(os.getenv("IMPORT_WORKER_BATCH_LIMIT", "1")))
    outcome = WorkerOutcome(requested_city_slug=city_slug)
    try:
        outcome = run_worker_loop(
            limit=min(1, configured_limit),
            sleep_seconds=max(5, int(os.getenv("IMPORT_WORKER_SLEEP_SECONDS", "60"))),
            actor_id=os.getenv("IMPORT_WORKER_ACTOR", "import-worker"),
            health_url=os.getenv("IMPORT_WORKER_BACKEND_HEALTH_URL", "http://backend:8000/ready"),
            max_runtime_seconds=int(os.getenv("IMPORT_WORKER_MAX_RUNTIME_SECONDS", "900")) or None,
            max_iterations=1,
            city_slug=city_slug,
            dry_run=is_dry_run,
            outcome=outcome,
        )
    except WorkerStopRequested as exc:
        print(str(exc), file=sys.stderr, flush=True)
        outcome.skip_reason = outcome.skip_reason or "stop_requested"
        _print_outcome(outcome.finalize(exit_code=0))
        return 0

    # safe_one_job must fail if no matching job was claimed or processed —
    # a healthy-looking run that quietly did nothing is not success. dry_run
    # is exempt: reporting an empty queue is its correct, successful outcome.
    if not is_dry_run and not outcome.claimed:
        outcome.skip_reason = outcome.skip_reason or (
            "no_matching_queued_job" if city_slug else "no_queued_job_available"
        )
        print(f"import_worker_no_matching_queued_job city_slug={city_slug!r} reason={outcome.skip_reason}", file=sys.stderr, flush=True)
        _print_outcome(outcome.finalize(exit_code=1))
        return 1

    # A claimed job that never reached a terminal status is always a
    # failure -- a stalled job must never look identical to "the worker ran
    # fine". "max_runtime_without_terminal_progress" is reserved for a
    # genuine timeout: it is only ever set by run_worker_loop's own runtime
    # check above (started_at ... max_runtime_seconds), never invented here.
    # Any other non-terminal outcome (e.g. the runner's finalize_import_job
    # call was rejected under lock -- lost ownership or already
    # terminalized by a concurrent stall-sweep/cancel) gets its own
    # truthful reason instead of being mislabeled as a timeout that never
    # actually happened.
    if not is_dry_run and outcome.claimed and not outcome.processed:
        if outcome.skip_reason != "max_runtime_without_terminal_progress":
            outcome.skip_reason = "job_finalize_did_not_reach_terminal_status"
        print(
            f"import_worker_job_did_not_reach_terminal_status job_id={outcome.matched_job_id} "
            f"status={outcome.terminal_status!r} reason={outcome.skip_reason} "
            f"claimed_by={outcome.claimed_by!r} expected_claimed_by={outcome.expected_claimed_by!r} "
            f"finished_at={outcome.finished_at!r}",
            file=sys.stderr,
            flush=True,
        )
        _print_outcome(outcome.finalize(exit_code=1))
        return 1

    _print_outcome(outcome.finalize(exit_code=0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
