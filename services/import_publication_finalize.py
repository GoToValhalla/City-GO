"""Finalize import publication: fresh snapshot evidence, place and city publish."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.admin_city_publication_service import publish_city
from services.canonical_publication_apply import apply_canonical_publication_verdict
from services.canonical_publication_guard import (
    SUCCESS_IMPORT_STATUSES,
    assess_place_import_decision,
    evaluate_canonical_publication,
    import_evidence_allows_publish,
)
from services.city_readiness.score import latest_city_readiness_snapshot, recalculate_city_readiness_snapshot
from services.review_queue_service import ensure_review_item


def finalize_import_publication(
    db: Session,
    *,
    city: City,
    job: CityAdminImportJob,
    place_ids: list[int],
    import_status: str,
) -> dict[str, object]:
    if not place_ids:
        return _skipped(job, "no_changed_places")
    if import_status not in SUCCESS_IMPORT_STATUSES:
        return _skipped(job, "import_not_successful", import_status=import_status)
    snapshot_payload = persist_import_readiness_snapshot(db, city_slug=city.slug, job_id=job.id)
    snapshot = latest_city_readiness_snapshot(db, city_slug=city.slug)
    snapshot_id = int(snapshot.id) if snapshot is not None else None
    snapshot_job_id = _snapshot_job_id(snapshot)
    allowed, block_reasons = import_evidence_allows_publish(
        job_status=import_status,
        snapshot_quality_status=str(snapshot.quality_status) if snapshot is not None else None,
        snapshot_job_id=snapshot_job_id,
        current_job_id=job.id,
        snapshot_created_at=snapshot.created_at if snapshot is not None else None,
    )
    counters = _empty_counters()
    places = _target_places(db, city.id, place_ids)
    for place in places:
        verdict = evaluate_canonical_publication(
            place,
            import_decision=assess_place_import_decision(place),
            evidence_allowed=allowed,
        )
        key = apply_canonical_publication_verdict(
            db, place, verdict, job_id=job.id, snapshot_id=snapshot_id,
        )
        counters[key] = counters.get(key, 0) + 1
        if verdict.outcome == "review":
            ensure_review_item(
                db, city_id=city.id, place_id=place.id, job_id=job.id,
                field_name="publication_status", reason=verdict.reasons[0],
            )
    if not allowed:
        return _publication_failure(job, block_reasons, counters=counters, snapshot=snapshot_payload)
    published_count = int(counters.get("auto_published", 0)) + int(counters.get("limited_published", 0))
    if published_count <= 0:
        preserved = int(counters.get("preserved_public", 0))
        if preserved > 0 and city.launch_status == "published":
            return {
                "status": "published",
                "idempotent": True,
                "snapshot_id": snapshot_id,
                "counters": counters,
                "city_published": True,
            }
        return _publication_failure(job, ("no_publishable_places",), counters=counters, snapshot=snapshot_payload)
    city_result = _maybe_publish_city(db, city=city, job=job, allowed=True, counters=counters)
    if city_result.get("city_publish_failed"):
        return _publication_failure(job, tuple(city_result["reasons"]), counters=counters, snapshot=snapshot_payload)
    return {
        "status": "published",
        "snapshot_id": snapshot_id,
        "counters": counters,
        "city_published": city_result.get("city_published", False),
        "readiness_score": snapshot_payload.get("readiness_score") if snapshot_payload else None,
    }


def persist_import_readiness_snapshot(db: Session, *, city_slug: str, job_id: int) -> dict[str, object] | None:
    payload = recalculate_city_readiness_snapshot(
        db, city_slug=city_slug, reason=f"import_job_{job_id}", recalculate_place_scores=True,
    )
    snapshot = latest_city_readiness_snapshot(db, city_slug=city_slug)
    if snapshot is None:
        return payload
    body = dict(snapshot.snapshot_payload or {})
    body["import_job_id"] = job_id
    body["import_job_finished_at"] = datetime.utcnow().isoformat()
    snapshot.snapshot_payload = body
    db.commit()
    return payload


def _maybe_publish_city(db: Session, *, city: City, job: CityAdminImportJob, allowed: bool, counters: dict[str, int]) -> dict[str, object]:
    if not allowed or city.launch_status == "published":
        return {"city_published": city.launch_status == "published"}
    published_count = int(counters.get("auto_published", 0)) + int(counters.get("limited_published", 0))
    if published_count <= 0:
        return {"city_published": False, "reasons": ("no_publishable_places",)}
    try:
        publish_city(db, city.id, actor="import_pipeline", reason=f"import_job_{job.id}")
        return {"city_published": True}
    except ValueError as exc:
        return {"city_publish_failed": True, "reasons": (str(exc),)}


def _target_places(db: Session, city_id: int, place_ids: list[int]) -> list[Place]:
    query = db.query(Place).filter(Place.city_id == city_id)
    if place_ids:
        query = query.filter(Place.id.in_(place_ids))
    return query.order_by(Place.id.asc()).all()


def _snapshot_job_id(snapshot) -> int | None:
    if snapshot is None:
        return None
    payload = snapshot.snapshot_payload or {}
    raw = payload.get("import_job_id")
    return int(raw) if raw is not None else None


def _empty_counters() -> dict[str, int]:
    return {"auto_published": 0, "limited_published": 0, "review_required": 0, "rejected": 0, "preserved_public": 0, "blocked": 0}


def _skipped(job: CityAdminImportJob, reason: str, **details: object) -> dict[str, object]:
    payload = {"status": "skipped", "reason": reason, **details}
    _store_publication_result(job, payload)
    return payload


def _publication_failure(job: CityAdminImportJob, reasons: tuple[str, ...], **details: object) -> dict[str, object]:
    payload = {"status": "failed", "reasons": list(reasons), **details}
    _store_publication_result(job, payload, downgrade_status=True)
    return payload


def _store_publication_result(job: CityAdminImportJob, payload: dict[str, object], *, downgrade_status: bool = False) -> None:
    details = dict(job.step_details or {})
    details["publication_finalize"] = payload
    job.step_details = details
