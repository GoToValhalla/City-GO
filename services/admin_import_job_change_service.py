"""Admin import run report persistence and queries."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_admin_import_job_change import CityAdminImportJobChange
from models.place import Place

CHANGE_TYPES = ("created", "updated", "unchanged", "rejected", "hidden", "needs_review")

def record_place_changes(db: Session, *, job: CityAdminImportJob, places: list[Place], since: datetime) -> int:
    db.query(CityAdminImportJobChange).filter(CityAdminImportJobChange.job_id == job.id).delete()
    rows = [_row(job=job, place=place, since=since) for place in places]
    db.add_all(rows)
    return len(rows)

def list_import_job_changes(
    db: Session, *, city_id: int, change_type: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[CityAdminImportJobChange], int]:
    job = latest_job(db, city_id)
    if job is None:
        return [], 0
    query = db.query(CityAdminImportJobChange).filter(CityAdminImportJobChange.job_id == job.id)
    if change_type:
        query = query.filter(CityAdminImportJobChange.change_type == change_type)
    total = query.count()
    rows = query.order_by(CityAdminImportJobChange.id.asc()).offset(offset).limit(limit).all()
    return rows, total

def import_job_changes_summary(db: Session, *, city_id: int) -> dict[str, Any] | None:
    city = db.query(City).filter(City.id == city_id).first()
    job = latest_job(db, city_id)
    if city is None or job is None:
        return None
    counts = Counter(
        row.change_type
        for row in db.query(CityAdminImportJobChange.change_type).filter(CityAdminImportJobChange.job_id == job.id)
    )
    if not counts:
        counts.update(_fallback_counts(job))
    return {"job_id": job.id, "city_id": city.id, "city_slug": city.slug, **_counts(counts)}

def latest_job(db: Session, city_id: int) -> CityAdminImportJob | None:
    return (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id)
        .order_by(CityAdminImportJob.created_at.desc(), CityAdminImportJob.id.desc())
        .first()
    )

def serialize_change(row: CityAdminImportJobChange) -> dict[str, Any]:
    keys = ("id", "job_id", "city_id", "place_id", "external_source_id", "change_type", "place_title", "category", "source", "reason", "created_at")
    return {key: getattr(row, key) for key in keys}

def _row(*, job: CityAdminImportJob, place: Place, since: datetime) -> CityAdminImportJobChange:
    return CityAdminImportJobChange(
        job_id=int(job.id),
        city_id=int(job.city_id),
        place_id=int(place.id),
        change_type=_change_type(place, since),
        place_title=place.title,
        category=place.category,
        source=place.source,
        reason=_reason(place),
        after_json={"publication_status": place.publication_status, "status": place.status},
    )

def _change_type(place: Place, since: datetime) -> str:
    if place.publication_status == "hidden" or place.status == "hidden" or not bool(place.is_active):
        return "hidden"
    if place.publication_status == "needs_review":
        return "created" if place.created_at and place.created_at >= since else "needs_review"
    return "created" if place.created_at and place.created_at >= since else "updated"

def _reason(place: Place) -> str | None:
    return place.publication_comment or place.route_exclusion_reason or place.admin_comment or place.publication_status

def _fallback_counts(job: CityAdminImportJob) -> dict[str, int]:
    details = job.step_details or {}
    diff = details.get("import_diff") or details.get("import_summary") or {}
    return {key: int(diff.get(key) or 0) for key in CHANGE_TYPES} if isinstance(diff, dict) else {}


def _counts(source: Counter | dict[str, int]) -> dict[str, int]:
    return {key: int(source.get(key, 0)) for key in CHANGE_TYPES}
