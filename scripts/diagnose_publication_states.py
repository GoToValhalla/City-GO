from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place

MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")


def latest_jobs_by_city(db: Session, city_ids: list[int]) -> dict[int, CityAdminImportJob]:
    if not city_ids:
        return {}
    rows = (
        db.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id.in_(city_ids))
        .order_by(CityAdminImportJob.city_id.asc(), CityAdminImportJob.created_at.desc(), CityAdminImportJob.id.desc())
        .all()
    )
    result: dict[int, CityAdminImportJob] = {}
    for job in rows:
        result.setdefault(int(job.city_id), job)
    return result


def place_counts(db: Session, city_ids: list[int]) -> dict[int, dict[str, int]]:
    result: dict[int, dict[str, int]] = defaultdict(dict)
    rows = db.query(Place.city_id, Place.publication_status, func.count(Place.id)).filter(Place.city_id.in_(city_ids)).group_by(Place.city_id, Place.publication_status).all()
    for city_id, status, count in rows:
        result[int(city_id)][str(status or "unknown")] = int(count or 0)
    metric_rows = db.query(
        Place.city_id,
        func.count(Place.id).label("total"),
        func.sum((Place.is_published.is_(True)).cast(db.bind.dialect.type_descriptor(func.count().type))).label("published"),
    ).filter(Place.city_id.in_(city_ids)).group_by(Place.city_id).all()
    for row in metric_rows:
        result[int(row.city_id)]["__total"] = int(row.total or 0)
        result[int(row.city_id)]["__published"] = int(row.published or 0)
    return result


def safe_count(db: Session, city_id: int, *conditions: Any) -> int:
    return int(db.query(func.count(Place.id)).filter(Place.city_id == city_id, *conditions).scalar() or 0)


def diagnose(city_slug: str | None = None) -> dict[str, Any]:
    with SessionLocal() as db:
        query = db.query(City).order_by(City.name.asc(), City.id.asc())
        if city_slug:
            query = query.filter(City.slug == city_slug)
        cities = query.all()
        city_ids = [int(city.id) for city in cities]
        latest_jobs = latest_jobs_by_city(db, city_ids)
        rows: list[dict[str, Any]] = []
        hidden_with_published_places: list[str] = []
        failed_but_published: list[str] = []
        manual_reasons: Counter[str] = Counter()
        auto_reasons: Counter[str] = Counter()

        for city in cities:
            job = latest_jobs.get(int(city.id))
            manual = safe_count(db, int(city.id), Place.publication_status.in_(MANUAL_REVIEW_STATUSES))
            auto = safe_count(db, int(city.id), Place.publication_status.in_(AUTO_BACKLOG_STATUSES))
            published = safe_count(db, int(city.id), Place.is_published.is_(True))
            visible = safe_count(db, int(city.id), Place.is_visible_in_catalog.is_(True))
            route = safe_count(db, int(city.id), Place.is_route_eligible.is_(True))
            total = safe_count(db, int(city.id))
            low_conf = safe_count(db, int(city.id), Place.existence_confidence_level.in_(("low", "unknown")))
            missing_address = safe_count(db, int(city.id), Place.address.is_(None))
            missing_photo = safe_count(db, int(city.id), Place.image_url.is_(None))
            rejected = safe_count(db, int(city.id), Place.publication_status == "rejected")
            draft = safe_count(db, int(city.id), Place.publication_status == "draft")
            if published and (not city.is_active or city.launch_status != "published"):
                hidden_with_published_places.append(city.slug)
            if job is not None and job.status in {"failed", "partial_success", "success_with_warnings", "import_failed"} and city.is_active and city.launch_status == "published":
                failed_but_published.append(city.slug)
            if manual:
                manual_reasons["publication_status_manual"] += manual
            if auto:
                auto_reasons["publication_status_auto_backlog"] += auto
            if missing_address:
                auto_reasons["missing_address"] += missing_address
            if missing_photo:
                auto_reasons["missing_photo"] += missing_photo
            rows.append(
                {
                    "slug": city.slug,
                    "name": city.name,
                    "is_active": bool(city.is_active),
                    "launch_status": city.launch_status,
                    "latest_import_status": job.status if job else None,
                    "readiness_score": city.readiness_score,
                    "quality_status": city.quality_status,
                    "places_total": total,
                    "places_published": published,
                    "places_visible": visible,
                    "places_route_eligible": route,
                    "places_draft": draft,
                    "places_auto_backlog": auto,
                    "places_manual_review": manual,
                    "places_low_confidence": low_conf,
                    "places_missing_address": missing_address,
                    "places_missing_photo": missing_photo,
                    "places_rejected": rejected,
                    "last_import_at": city.last_import_at.isoformat() if city.last_import_at else None,
                    "latest_job_id": job.id if job else None,
                    "latest_job_error": job.last_error if job else None,
                }
            )
        return {
            "active_cities_count": sum(1 for city in cities if city.is_active and city.launch_status == "published"),
            "published_cities_count": sum(1 for city in cities if city.launch_status == "published"),
            "cities_with_import_failed_but_published_product_state": failed_but_published,
            "cities_incorrectly_hidden_while_having_published_places": hidden_with_published_places,
            "top_reasons_manual_queue": manual_reasons.most_common(20),
            "top_reasons_auto_backlog": auto_reasons.most_common(20),
            "cities": rows,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--city-slug")
    args = parser.parse_args()
    payload = diagnose(city_slug=args.city_slug)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
