"""Finalize import evidence: fresh readiness snapshot + publication proposal.

Blocker fix (post-CITYGO-339..344): this module must NEVER call
publish_city()/publish_place() or set any city/place publication or
visibility flag. A successful import only produces evidence (a fresh
readiness snapshot) and a publication PROPOSAL — recorded
PlacePublicationDecision rows plus the city moved to the existing
"review_required" workflow state (a metadata marker, not a visibility
flag; see models/city.py's launch_status and the identical precedent in
services/import_pipeline/enrichment_only.py). Only an explicit,
authenticated admin action (services/admin_service.py's publish_place,
services/admin_city_publication_service.py's publish_city, reached only
through routers/admin*.py endpoints) may ever flip is_active/is_published/
is_visible_in_catalog/launch_status="published".
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.canonical_publication_apply import apply_canonical_publication_verdict
from services.canonical_publication_guard import (
    SUCCESS_IMPORT_STATUSES,
    assess_place_import_decision,
    evaluate_canonical_publication,
    import_evidence_allows_publish,
)
from services.city_readiness.score import latest_city_readiness_snapshot, recalculate_city_readiness_snapshot
from services.review_queue_service import ensure_review_item

CITY_STATUS_REVIEW_REQUIRED = "review_required"
CITY_STATUS_PUBLISHED = "published"


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
        # record_only=True: a successful import produces a publication
        # PROPOSAL (a recorded PlacePublicationDecision + review item), it
        # must never itself flip is_published/is_visible_in_catalog/etc. on
        # a place. Hard-safety archiving/review-marking for genuinely bad
        # data (invalid coordinates, hard-excluded categories) still
        # applies unconditionally — see
        # canonical_publication_apply.apply_canonical_publication_verdict's
        # own docstring for why that is quality enforcement, not "publish".
        key = apply_canonical_publication_verdict(
            db, place, verdict, job_id=job.id, snapshot_id=snapshot_id, record_only=True,
        )
        counters[key] = counters.get(key, 0) + 1
        if verdict.outcome == "review":
            ensure_review_item(
                db, city_id=city.id, place_id=place.id, job_id=job.id,
                field_name="publication_status", reason=verdict.reasons[0],
            )
    if not allowed:
        return _publication_failure(job, block_reasons, counters=counters, snapshot=snapshot_payload)
    proposable_count = int(counters.get("review_required", 0)) + int(counters.get("preserved_public", 0))
    if proposable_count <= 0:
        return _publication_failure(job, ("no_publishable_places",), counters=counters, snapshot=snapshot_payload)
    city_marked = _mark_city_ready_for_review(city)
    return {
        "status": "ready_for_review",
        "snapshot_id": snapshot_id,
        "counters": counters,
        "city_marked_ready_for_review": city_marked,
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


def _mark_city_ready_for_review(city: City) -> bool:
    """Blocker fix: this NEVER calls publish_city() and never sets
    is_active/is_published/is_visible_in_catalog. It only moves the city's
    workflow-state marker to the existing "review_required" launch_status
    (same precedent as services/import_pipeline/enrichment_only.py) so an
    admin sees the city needs a publication decision. An already-published
    city is left untouched — evidence from a later import must never
    downgrade a live city's status either."""
    if city.launch_status == CITY_STATUS_PUBLISHED:
        return False
    city.launch_status = CITY_STATUS_REVIEW_REQUIRED
    return True


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
