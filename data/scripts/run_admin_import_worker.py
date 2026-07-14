"""Persistent import worker loop with bounded health and shutdown behavior."""

from __future__ import annotations

import os
import signal
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from db.session import SessionLocal
from services.admin_alert_service import send_admin_alert
from services.admin_city_import_tasks import import_queue_summary, run_queued_import_jobs

_STOP = False

RUN_MODE_SAFE_ONE_JOB = "safe_one_job"
RUN_MODE_DRY_RUN = "dry_run"
RUN_MODE_DIAGNOSTICS_ONLY = "diagnostics_only"


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
) -> bool:
    """Returns True if at least one queued job was found (claimed, or would
    have been claimed under dry_run) during the loop; False otherwise."""
    found_job = False
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
            break
        if not backend_is_healthy(health_url):
            print(f"import_worker_backend_unhealthy url={health_url}", file=sys.stderr, flush=True)
            send_admin_alert(
                title="Import-worker остановлен: backend недоступен",
                message=f"Import-worker прекращает обработку: backend health check ({health_url}) не прошёл.",
                level="error",
                details={"status": "backend_unhealthy", "health_url": health_url},
            )
            break
        iteration += 1
        try:
            result = run_queued_import_jobs(actor_id=actor_id, limit=limit, city_slug=city_slug, dry_run=dry_run)
            if dry_run:
                would_process = result.get("would_process") or []
                print(f"import_worker_dry_run would_process={would_process}", flush=True)
                if would_process:
                    found_job = True
            elif int(result.get("processed") or 0) + int(result.get("failed") or 0) > 0:
                # A claimed-but-failed job still means a matching job existed
                # for this city_slug — that is a job-execution outcome, not
                # an "empty queue" outcome, and must not be conflated with it.
                found_job = True
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
        if not _STOP and (max_iterations is None or iteration < max_iterations):
            time.sleep(sleep_seconds)
    return found_job


def run_diagnostics_only(*, city_slug: str | None = None) -> None:
    """Read-only queue report. Performs no claim, no job execution, no
    mutation of any kind — not even stalled-job marking."""
    with SessionLocal() as db:
        summary = import_queue_summary(db)
    if city_slug:
        summary = {**summary, "city_slug_filter": city_slug}
    print(f"import_worker_diagnostics_only queue={summary}", flush=True)


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

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
    found_job = False
    try:
        found_job = run_worker_loop(
            limit=min(1, configured_limit),
            sleep_seconds=max(5, int(os.getenv("IMPORT_WORKER_SLEEP_SECONDS", "60"))),
            actor_id=os.getenv("IMPORT_WORKER_ACTOR", "import-worker"),
            health_url=os.getenv("IMPORT_WORKER_BACKEND_HEALTH_URL", "http://backend:8000/ready"),
            max_runtime_seconds=int(os.getenv("IMPORT_WORKER_MAX_RUNTIME_SECONDS", "300")) or None,
            max_iterations=1,
            city_slug=city_slug,
            dry_run=is_dry_run,
        )
    except WorkerStopRequested as exc:
        print(str(exc), file=sys.stderr, flush=True)
        return 0

    if city_slug and not found_job:
        print(f"import_worker_no_matching_queued_job city_slug={city_slug!r}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
