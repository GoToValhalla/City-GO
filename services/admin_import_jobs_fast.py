from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from services.admin_extended_service import _city_counters, _import_job_list_payload, _latest_import_jobs


def list_admin_import_jobs_fast(db: Session, *, limit: int = 50, offset: int = 0) -> dict[str, object]:
    """Fast list read-model for /admin/import-jobs.

    The mobile admin screen must stay lightweight while import-worker is busy.
    Full snapshot/details are still available through GET /admin/import-jobs/{city_id}.
    The list endpoint intentionally avoids scanning historical import jobs with large
    step_details JSON blobs for latest snapshots.
    """
    query = (
        db.query(City)
        .filter(City.launch_status.in_(("importing", "imported", "review_required", "import_failed", "published")))
        .order_by(City.updated_at.desc(), City.id.desc())
    )
    total = query.count()
    cities = query.offset(offset).limit(limit).all()
    city_ids = [city.id for city in cities]
    counters = _city_counters(db, city_ids)
    latest_jobs = _latest_import_jobs(db, city_ids)
    return {
        "items": [
            _import_job_list_payload(
                city,
                counters=counters.get(city.id),
                job=latest_jobs.get(city.id),
                snapshot=None,
            )
            for city in cities
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
