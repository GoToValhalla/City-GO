"""Persistent import worker loop with rate-limited failure and recovery alerts."""

from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.admin_alert_service import send_admin_alert
from services.admin_city_import_tasks import run_queued_import_jobs

_STOP = False


def _stop(_signum, _frame) -> None:
    global _STOP
    _STOP = True


def run_worker_loop(
    *,
    limit: int,
    sleep_seconds: int,
    actor_id: str = "import-worker",
    max_iterations: int | None = None,
) -> None:
    consecutive_failures = 0
    iteration = 0
    while not _STOP and (max_iterations is None or iteration < max_iterations):
        iteration += 1
        try:
            result = run_queued_import_jobs(actor_id=actor_id, limit=limit)
            if consecutive_failures:
                send_admin_alert(
                    title="Import worker recovered",
                    message=f"Import-worker снова работает после {consecutive_failures} ошибок подряд.",
                    level="info",
                    details={"status": "recovered", "previous_failures": consecutive_failures, "queue": result.get("queue")},
                )
            consecutive_failures = 0
        except Exception as exc:  # noqa: BLE001
            consecutive_failures += 1
            # Notify immediately, after the third failure, and then every tenth failure.
            if consecutive_failures in {1, 3} or consecutive_failures % 10 == 0:
                send_admin_alert(
                    title="Import worker loop failed",
                    message=str(exc)[:1000],
                    level="error",
                    details={"status": "failed", "consecutive_failures": consecutive_failures},
                )
            print(f"import_worker_loop_failed count={consecutive_failures}: {exc}", file=sys.stderr, flush=True)
        if not _STOP and (max_iterations is None or iteration < max_iterations):
            time.sleep(sleep_seconds)


def main() -> int:
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    run_worker_loop(
        limit=max(1, int(os.getenv("IMPORT_WORKER_BATCH_LIMIT", "1"))),
        sleep_seconds=max(5, int(os.getenv("IMPORT_WORKER_SLEEP_SECONDS", "60"))),
        actor_id=os.getenv("IMPORT_WORKER_ACTOR", "import-worker"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
