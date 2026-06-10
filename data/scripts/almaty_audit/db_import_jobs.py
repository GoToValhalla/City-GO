"""Import jobs CSV для Алматы."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.import_batch import ImportBatch


def write_import_jobs(db: Session, out: Path, slugs: tuple[str, ...]) -> int:
    city = db.query(City).filter(City.slug.in_(slugs)).first()
    if city is None:
        out.write_text("", encoding="utf-8")
        return 0
    fields = [
        "id", "city_slug", "source", "status", "created_at", "started_at", "finished_at",
        "total", "processed", "created_places", "updated_places", "skipped_places",
        "failed_places", "last_error", "metadata_json",
    ]
    admin_jobs = db.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).all()
    batches = db.query(ImportBatch).filter(ImportBatch.city_id == city.id).all()
    rows: list[dict[str, object]] = []
    for j in admin_jobs:
        rows.append({
            "id": f"admin-{j.id}", "city_slug": city.slug, "source": j.source, "status": j.status,
            "created_at": j.created_at, "started_at": j.started_at, "finished_at": j.finished_at,
            "total": j.scopes_total, "processed": j.scopes_succeeded,
            "created_places": j.places_saved, "updated_places": 0, "skipped_places": 0,
            "failed_places": max(j.scopes_total - j.scopes_succeeded, 0),
            "last_error": j.last_error,
            "metadata_json": json.dumps({"places_found": j.places_found}),
        })
    for b in batches:
        meta = {
            "raw_count": b.raw_count, "normalized_count": b.normalized_count,
            "published_count": b.published_count, "needs_review_count": b.needs_review_count,
            "rejected_count": b.rejected_count, "duplicate_count": b.duplicate_count,
            "errors_count": b.errors_count, "diff_summary": b.diff_summary,
        }
        rows.append({
            "id": f"batch-{b.id}", "city_slug": city.slug, "source": "import_batch",
            "status": b.status, "created_at": b.created_at, "started_at": b.started_at,
            "finished_at": b.finished_at, "total": b.raw_count,
            "processed": b.normalized_count,
            "created_places": b.published_count, "updated_places": 0,
            "skipped_places": b.duplicate_count, "failed_places": b.rejected_count,
            "last_error": None if b.errors_count == 0 else f"errors_count={b.errors_count}",
            "metadata_json": json.dumps(meta, ensure_ascii=False, default=str),
        })
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows)
