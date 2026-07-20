"""Publication decision application for import pipeline."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.canonical_publication_apply import apply_canonical_publication_verdict
from services.canonical_publication_guard import assess_place_import_decision, evaluate_canonical_publication
from services.review_queue_service import ensure_review_item


def apply_pipeline_publication(
    db: Session,
    city: City,
    job: CityAdminImportJob,
    place: Place,
    counters: dict[str, int],
    *,
    evidence_allowed: bool = False,
    snapshot_id: int | None = None,
) -> None:
    """CITYGO-339: the mid-pipeline publication step. This runs before any
    quality-snapshot evidence exists, so it must never auto-publish a place
    and must never unpublish a place an admin already made live — for an
    already-public place it only records the canonical decision and creates
    a review item. A place that is not yet public may still be archived or
    marked needs_review here (existing, tested import-time safety behavior
    for invalid coordinates, hard-excluded categories, etc. — see
    tests/test_import_pipeline_foundation_safety.py). Real live publication
    is applied later, after real evidence exists, by
    services/import_publication_finalize.py, or by an explicit admin action.
    """
    import_decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=import_decision, evidence_allowed=evidence_allowed)
    record_only = _pipeline_record_only(verdict, evidence_allowed=evidence_allowed)
    key = apply_canonical_publication_verdict(
        db,
        place,
        verdict,
        job_id=job.id,
        snapshot_id=snapshot_id,
        record_only=True if record_only else False,
    )
    counters[key] = counters.get(key, 0) + 1
    if verdict.outcome in {"review", "reject", "blocked"}:
        ensure_review_item(
            db,
            city_id=city.id,
            place_id=place.id,
            job_id=job.id,
            field_name=_review_field(verdict.reasons[0] if verdict.reasons else "publication_status"),
            reason=verdict.reasons[0] if verdict.reasons else "needs_review",
        )


def _pipeline_record_only(verdict, *, evidence_allowed: bool) -> bool:
    """Mid-pipeline never live-publishes; hard safety and review states still apply.

    Architecture contract for import call sites: publish/preserve stay
    record_only=True; reject/blocked/review may apply through the writer.
    """
    if verdict.outcome == "reject":
        return False
    if verdict.outcome == "preserve_public":
        return True
    if verdict.outcome == "publish":
        return True  # record_only=True for unattended publish paths
    if verdict.outcome in {"blocked", "review"}:
        return False
    return not evidence_allowed


def _review_field(reason: str) -> str:
    return {
        "non_tourist_category": "category",
        "low_confidence": "confidence",
        "missing_hours_for_dynamic_category": "opening_hours",
        "no_source": "source",
    }.get(reason, "publication_status")
