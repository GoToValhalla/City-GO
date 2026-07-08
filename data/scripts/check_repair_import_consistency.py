"""Find and safely repair stale import/job/city state after failed imports.

Checks (report always; repair only where marked SAFE APPLY below):
1. Stale running import jobs (no heartbeat past STALL_THRESHOLD_MINUTES).
   SAFE APPLY: mark stalled using the existing recovery convention
   (services.admin_city_import_tasks.mark_stalled_import_jobs).
2. Completed jobs (success/success_with_warnings/partial_success/imported)
   with no admin_import_snapshot in step_details.
   Report only: no existing job-level needs-review status to apply.
3. Published city with no snapshot on its latest job.
   Report only: never unpublish.
4. Published city whose latest import is failed/stalled/import_failed.
   Report only: never unpublish.
5. City stats mismatch (job.places_found/places_saved vs actual Place rows).
   Report only: no existing safe repair helper for this in scope
   (city_readiness recalculation exists but is quality-scoring, out of scope).

Usage:
    python -m data.scripts.check_repair_import_consistency --dry-run
    python -m data.scripts.check_repair_import_consistency --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_import_job_payload import SNAPSHOT_KEY
from services.admin_city_import_tasks import mark_stalled_import_jobs
from services.admin_import_display import FAILED_IMPORT_STATUSES, is_published_city
from services.import_pipeline.progress import is_stalled

REVIEWABLE_JOB_STATUSES = {"success", "success_with_warnings", "partial_success", "imported"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only (default).")
    parser.add_argument("--apply", action="store_true", help="Apply safe repairs (stale running jobs only).")
    parser.add_argument("--actor-id", default="check_repair_import_consistency", help="Actor id recorded on any applied repair.")
    args = parser.parse_args(argv)
    if args.apply and args.dry_run:
        raise SystemExit("Choose either --dry-run or --apply, not both.")
    return args


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    apply_mode = bool(args.apply)

    with SessionLocal() as db:
        report: dict[str, Any] = {
            "checked_at": datetime.utcnow().isoformat(),
            "mode": "apply" if apply_mode else "dry_run",
            "stale_running_jobs": _check_stale_running_jobs(db, apply_mode=apply_mode, actor_id=args.actor_id),
            "completed_jobs_without_snapshot": _check_completed_jobs_without_snapshot(db),
            "published_cities_missing_snapshot": _check_published_cities_missing_snapshot(db),
            "published_cities_with_failed_import": _check_published_cities_with_failed_import(db),
            "city_stats_mismatch": _check_city_stats_mismatch(db),
        }
        return report


def _check_stale_running_jobs(db: Session, *, apply_mode: bool, actor_id: str) -> dict[str, Any]:
    now = datetime.utcnow()
    running = db.query(CityAdminImportJob).filter(CityAdminImportJob.status == "running").all()
    stale = [job for job in running if is_stalled(job, now=now)]
    found = [
        {"job_id": int(job.id), "city_id": int(job.city_id), "current_step": job.current_step, "updated_at": _iso(job.updated_at)}
        for job in stale
    ]
    result: dict[str, Any] = {"found": found, "count": len(found), "repaired": 0}
    if apply_mode and stale:
        result["repaired"] = mark_stalled_import_jobs(db, actor_id=actor_id, now=now)
    return result


def _check_completed_jobs_without_snapshot(db: Session) -> dict[str, Any]:
    jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.status.in_(REVIEWABLE_JOB_STATUSES)).all()
    found = []
    for job in jobs:
        snapshot = (job.step_details or {}).get(SNAPSHOT_KEY)
        if not isinstance(snapshot, dict):
            found.append({"job_id": int(job.id), "city_id": int(job.city_id), "status": job.status})
    return {"found": found, "count": len(found), "repaired": 0, "note": "report only: no job-level needs-review status exists to apply"}


def _check_published_cities_missing_snapshot(db: Session) -> dict[str, Any]:
    found = []
    for city in db.query(City).filter(City.launch_status == "published", City.is_active.is_(True)).all():
        job = _latest_job(db, city.id)
        snapshot = (job.step_details or {}).get(SNAPSHOT_KEY) if job is not None else None
        if not isinstance(snapshot, dict):
            found.append({"city_id": int(city.id), "city_slug": city.slug, "job_id": int(job.id) if job is not None else None})
    return {"found": found, "count": len(found), "repaired": 0, "note": "report only: never unpublish"}


def _check_published_cities_with_failed_import(db: Session) -> dict[str, Any]:
    found = []
    for city in db.query(City).filter(City.launch_status == "published").all():
        if not is_published_city(city):
            continue
        job = _latest_job(db, city.id)
        if job is None:
            continue
        if job.status in FAILED_IMPORT_STATUSES or is_stalled(job):
            found.append({"city_id": int(city.id), "city_slug": city.slug, "job_id": int(job.id), "job_status": job.status})
    return {"found": found, "count": len(found), "repaired": 0, "note": "report only: never unpublish"}


def _check_city_stats_mismatch(db: Session) -> dict[str, Any]:
    found = []
    for city in db.query(City).all():
        job = _latest_job(db, city.id)
        if job is None or job.status not in REVIEWABLE_JOB_STATUSES:
            continue
        actual_places = int(db.query(func.count(Place.id)).filter(Place.city_id == city.id).scalar() or 0)
        if int(job.places_saved or 0) != actual_places:
            found.append({
                "city_id": int(city.id),
                "city_slug": city.slug,
                "job_id": int(job.id),
                "job_places_saved": int(job.places_saved or 0),
                "actual_places": actual_places,
            })
    return {
        "found": found,
        "count": len(found),
        "repaired": 0,
        "note": "report only: no existing safe stats-repair helper in scope (city_readiness recalculation is quality scoring, excluded)",
    }


def _latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city_id).order_by(CityAdminImportJob.created_at.desc()).first()


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


if __name__ == "__main__":
    result = run()
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
