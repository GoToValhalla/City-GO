"""Legacy repair for CityAdminImportJob rows corrupted by the old
reset-in-place lifecycle bug (production Job #1: a terminal row was reset
back to status="queued" and reused across separate worker runs, mixing
timelines/counters from unrelated executions).

This script never deletes or rewrites history. It only:
1. Identifies rows whose status/started_at/finished_at combination is
   internally contradictory (the exact corruption shape) and marks them
   with lifecycle_flag="legacy_corrupted" so the diagnostic view surfaces
   them honestly instead of presenting the contradiction as a normal
   in-progress job.
2. Never invents missing execution boundaries — a flagged row's own
   status/timestamps/counters are left exactly as found.
3. Optionally (--create-retry-for CITY_SLUG), after flagging, creates a
   fresh queued row for that city through the normal
   services.admin_city_import_job_service.retry_import_job /
   queue_city_import_job service path (never by direct row manipulation) —
   but only if the city currently has no active (queued/running) row,
   exactly like any other retry.

Usage:
    python -m data.scripts.repair_import_job_lifecycle --dry-run
    python -m data.scripts.repair_import_job_lifecycle --apply
    # Operator has decided job #1's true outcome was a failure — flag it,
    # force it terminal, then let the normal retry path create a new row:
    python -m data.scripts.repair_import_job_lifecycle --apply \
        --force-terminal-status failed --force-terminal-job-id 1 \
        --create-retry-for almaty
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city_admin_import_job import CityAdminImportJob
from services.admin_city_import_job_service import DuplicateActiveJobError, retry_import_job
from services.admin_city_import_log import log_import_event
from services.city_slug_resolver import resolve_city_by_slug

_TERMINAL_STATUSES = frozenset({"success", "success_with_warnings", "partial_success", "failed", "cancelled", "stalled"})
# force-terminal-status only accepts genuinely terminal statuses: this is
# the one place outside _transition() allowed to write job.status
# directly, and only for a row already identified as legacy_corrupted, so
# it must not be usable to invent a queued/running state.
_FORCE_TERMINAL_ALLOWED = _TERMINAL_STATUSES


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Report only (default).")
    parser.add_argument("--apply", action="store_true", help="Flag corrupted rows with lifecycle_flag.")
    parser.add_argument("--create-retry-for", default=None, metavar="CITY_SLUG", help="After flagging, create a fresh queued retry row for this city via the normal service path.")
    parser.add_argument(
        "--force-terminal-status",
        default=None,
        metavar="STATUS",
        choices=sorted(_FORCE_TERMINAL_ALLOWED),
        help=(
            "Operator-approved: for the specific job named by --force-terminal-job-id, "
            "set its status to this explicit terminal value (never queued/running) so "
            "the city's partial unique index no longer treats it as active. Requires "
            "the row to already carry lifecycle_flag=legacy_corrupted (this run's flag "
            "pass, or a prior one) — this script never resolves ambiguity by guessing, "
            "the operator names the exact job and the exact terminal status."
        ),
    )
    parser.add_argument("--force-terminal-job-id", type=int, default=None, metavar="JOB_ID", help="The exact job_id --force-terminal-status applies to.")
    parser.add_argument("--actor-id", default="repair_import_job_lifecycle", help="Actor id recorded on any applied change.")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        raise SystemExit("Choose either --dry-run or --apply, not both.")
    if args.create_retry_for and not args.apply:
        raise SystemExit("--create-retry-for requires --apply.")
    if bool(args.force_terminal_status) != bool(args.force_terminal_job_id):
        raise SystemExit("--force-terminal-status and --force-terminal-job-id must be used together.")
    if args.force_terminal_status and not args.apply:
        raise SystemExit("--force-terminal-status requires --apply.")
    return args


def _is_corrupted(job: CityAdminImportJob) -> str | None:
    """Same detection as services/admin_import_job_diagnostic_service.py's
    _legacy_corruption, kept independent on purpose: this script must not
    depend on the diagnostic view's own logic changing shape under it."""
    if job.lifecycle_flag:
        return None  # already flagged, nothing new to do
    if job.status == "queued" and (job.started_at is not None or job.finished_at is not None):
        return "status=queued but started_at/finished_at already set"
    if job.status == "running" and job.finished_at is not None:
        return "status=running but finished_at already set"
    if job.status in _TERMINAL_STATUSES and job.started_at is None:
        return "terminal status but started_at was never set"
    return None


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    apply_mode = bool(args.apply)

    with SessionLocal() as db:
        report: dict[str, Any] = {
            "checked_at": datetime.utcnow().isoformat(),
            "mode": "apply" if apply_mode else "dry_run",
            "flagged": _flag_corrupted_jobs(db, apply_mode=apply_mode, actor_id=args.actor_id),
        }
        if apply_mode and args.force_terminal_status:
            report["forced_terminal"] = _force_terminal(
                db, job_id=args.force_terminal_job_id, status=args.force_terminal_status, actor_id=args.actor_id
            )
        if apply_mode and args.create_retry_for:
            report["retry_created"] = _create_retry(db, city_slug=args.create_retry_for, actor_id=args.actor_id)
        return report


def _force_terminal(db: Session, *, job_id: int, status: str, actor_id: str) -> dict[str, Any]:
    if status not in _FORCE_TERMINAL_ALLOWED:
        return {"ok": False, "reason": f"status must be one of {sorted(_FORCE_TERMINAL_ALLOWED)}"}
    job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
    if job is None:
        return {"ok": False, "reason": f"job not found: {job_id}"}
    if job.lifecycle_flag != "legacy_corrupted":
        return {"ok": False, "reason": "job is not flagged legacy_corrupted — run the flagging pass first"}
    old_status = job.status
    job.status = status
    if job.finished_at is None:
        job.finished_at = datetime.utcnow()
    log_import_event(
        db,
        event="import_job_legacy_forced_terminal",
        city_slug=None,
        actor_id=actor_id,
        level="warning",
        message=f"Job #{job.id} forced from status={old_status} to terminal status={status} by operator repair",
        details={"job_id": job.id, "from_status": old_status, "to_status": status},
        job_id=job.id,
    )
    db.commit()
    return {"ok": True, "job_id": int(job.id), "from_status": old_status, "to_status": status}


def _flag_corrupted_jobs(db: Session, *, apply_mode: bool, actor_id: str) -> dict[str, Any]:
    jobs = db.query(CityAdminImportJob).all()
    found: list[dict[str, Any]] = []
    for job in jobs:
        reason = _is_corrupted(job)
        if reason is None:
            continue
        entry = {
            "job_id": int(job.id),
            "city_id": int(job.city_id),
            "status": job.status,
            "started_at": _iso(job.started_at),
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            "reason": reason,
        }
        found.append(entry)
        if apply_mode:
            job.lifecycle_flag = "legacy_corrupted"
            log_import_event(
                db,
                event="import_job_legacy_corrupted_flagged",
                city_slug=None,
                actor_id=actor_id,
                level="warning",
                message=f"Job #{job.id} flagged legacy_corrupted: {reason}",
                details=entry,
                job_id=job.id,
            )
    if apply_mode and found:
        db.commit()
    return {"found": found, "count": len(found), "flagged": len(found) if apply_mode else 0}


def _create_retry(db: Session, *, city_slug: str, actor_id: str) -> dict[str, Any]:
    city = resolve_city_by_slug(db, city_slug)
    if city is None:
        return {"ok": False, "reason": f"city not found: {city_slug}"}
    try:
        job = retry_import_job(db, city_id=city.id, actor_id=actor_id)
        db.commit()
    except DuplicateActiveJobError as exc:
        return {"ok": False, "reason": "duplicate_active_job", "existing_job_id": exc.job_id, "existing_status": exc.job_status}
    except ValueError as exc:
        return {"ok": False, "reason": str(exc)}
    return {"ok": True, "job_id": int(job.id), "previous_job_id": job.previous_job_id, "status": job.status}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
