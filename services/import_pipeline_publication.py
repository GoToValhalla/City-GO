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
    import_decision = assess_place_import_decision(place)
    verdict = evaluate_canonical_publication(place, import_decision=import_decision, evidence_allowed=evidence_allowed)
    key = apply_canonical_publication_verdict(db, place, verdict, job_id=job.id, snapshot_id=snapshot_id)
    counters[key] = counters.get(key, 0) + 1
    if verdict.outcome == "review":
        ensure_review_item(
            db,
            city_id=city.id,
            place_id=place.id,
            job_id=job.id,
            field_name=_review_field(verdict.reasons[0] if verdict.reasons else "publication_status"),
            reason=verdict.reasons[0] if verdict.reasons else "needs_review",
        )


def _review_field(reason: str) -> str:
    return {
        "non_tourist_category": "category",
        "low_confidence": "confidence",
        "missing_hours_for_dynamic_category": "opening_hours",
        "no_source": "source",
    }.get(reason, "publication_status")
