"""Pure-ish step handlers for Stage 1 import pipeline foundation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.import_batch import ImportBatch
from models.place import Place
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.import_pipeline_publication import apply_pipeline_publication
from services.place_enrichment_sources import enrich_places_from_sources
from services.place_field_confidence_service import is_protected, upsert_field_confidence
from services.place_photo_candidate_service import add_photo_candidate
from services.review_queue_service import ensure_review_item

ENRICHMENT_CONFIDENCE_SOURCES = {"geoapify", "wikidata", "official_site", "citygo_category_rules"}
PROTECTED_PLACE_FIELDS = {
    "address": "address",
    "website": "website",
    "phone": "phone",
    "opening_hours": "opening_hours",
    "description": "short_description",
    "atmosphere": "atmosphere",
    "inside": "inside",
    "best_for": "best_for",
}


def run_step(db: Session, *, step: str, city: City, job: CityAdminImportJob, batch: ImportBatch, places: list[Place], counters: dict[str, int]) -> None:
    actions = {
        "collect_places": lambda: tuple(_observe_place(db, batch, city, place) for place in places),
        "normalize_categories": lambda: None,
        "backfill_addresses": lambda: None,
        "enrich_external_sources": lambda: _enrich_external_sources(db, city, job, batch, places, counters),
        "generate_ai_descriptions": lambda: tuple(_ai_description(db, place, job.id) for place in places),
        "fetch_photo_candidates": lambda: tuple(_photo_candidate(db, place) for place in places if place.image_url),
        "calculate_field_confidence": lambda: tuple(_confidence(db, place, job.id) for place in places),
        "apply_publication_decisions": lambda: tuple(apply_pipeline_publication(db, city, job, place, counters) for place in places),
    }
    actions[step]()


def _enrich_external_sources(
    db: Session,
    city: City,
    job: CityAdminImportJob,
    batch: ImportBatch,
    places: list[Place],
    counters: dict[str, int],
) -> None:
    protected_values: list[tuple[Place, str, object]] = []
    for place in places:
        for field_name, attribute in PROTECTED_PLACE_FIELDS.items():
            if is_protected(_field_row(db, place.id, field_name)):
                protected_values.append((place, attribute, getattr(place, attribute, None)))

    enrich_places_from_sources(
        db,
        city=city,
        batch=batch,
        places=places,
        job_id=job.id,
        counters=counters,
    )

    # Provider collectors can propose values, but manual confidence owns the
    # public field. Restore the protected value after collecting observations.
    for place, attribute, value in protected_values:
        setattr(place, attribute, value)


def _observe_place(db: Session, batch: ImportBatch, city: City, place: Place) -> None:
    external_id = f"place:{place.id}"
    payload = {"title": place.title, "category": place.category, "lat": place.lat, "lng": place.lng}
    row = db.query(SourceObservation).filter_by(city_id=city.id, source_external_id=external_id).first()
    row = row or SourceObservation(import_batch_id=batch.id, city_id=city.id, source_external_id=external_id)
    row.seen_in_batch_id = batch.id
    row.raw_payload = payload
    row.payload_hash = _payload_hash(payload)
    row.raw_name = place.title
    row.raw_category = place.category
    row.raw_lat = place.lat
    row.raw_lng = place.lng
    row.canonical_place_id = place.id
    row.last_seen_at = datetime.utcnow()
    db.add(row)


def _ai_description(db: Session, place: Place, job_id: int | None) -> None:
    existing = _field_row(db, place.id, "description")
    if place.short_description or is_protected(existing):
        return
    review = _open_field_review(db, place.id, "description")
    if review is not None:
        review.reason = "description_missing"
        review.job_id = job_id
        db.add(review)
        return
    ensure_review_item(
        db,
        city_id=place.city_id,
        place_id=place.id,
        job_id=job_id,
        field_name="description",
        reason="description_missing",
    )


def _photo_candidate(db: Session, place: Place) -> None:
    source = "category_fallback" if (place.source or "").startswith("category") else "existing_place_image"
    match = "category_fallback" if source == "category_fallback" else "exact"
    add_photo_candidate(db, place_id=place.id, image_url=place.image_url, source_type=source, match_type=match, confidence=0.4 if match != "exact" else 0.8)


def _confidence(db: Session, place: Place, job_id: int | None) -> None:
    fields = {
        "title": place.title,
        "coordinates": [place.lat, place.lng],
        "address": place.address,
        "website": getattr(place, "website", None),
        "phone": getattr(place, "phone", None),
        "category": place.category,
        "opening_hours": place.opening_hours,
        "description": place.short_description,
        "photo": place.image_url,
    }
    tuple(_confidence_field(db, place, job_id, field, value) for field, value in fields.items())


def _confidence_field(db: Session, place: Place, job_id: int | None, field: str, value: object) -> None:
    existing = _field_row(db, place.id, field)
    if existing is not None and existing.source_type in ENRICHMENT_CONFIDENCE_SOURCES and value not in (None, "", [], {}):
        return
    confidence = _confidence_value(field, value)
    row, changed = upsert_field_confidence(db, place_id=place.id, field_name=field, confidence=confidence, source_type=place.source or "import")
    if changed and row.confidence_level == "low" and value not in (None, "", [], {}):
        ensure_review_item(db, city_id=place.city_id, place_id=place.id, job_id=job_id, field_name=field, reason="low_confidence")


def _field_row(db: Session, place_id: int, field_name: str):
    from models.place_field_confidence import PlaceFieldConfidence

    for pending in db.new:
        if isinstance(pending, PlaceFieldConfidence) and pending.place_id == place_id and pending.field_name == field_name:
            return pending
    return db.query(PlaceFieldConfidence).filter_by(place_id=place_id, field_name=field_name).first()


def _open_field_review(db: Session, place_id: int, field_name: str) -> ReviewQueueItem | None:
    for pending in db.new:
        if (
            isinstance(pending, ReviewQueueItem)
            and pending.place_id == place_id
            and pending.field_name == field_name
            and pending.status == "open"
        ):
            return pending
    return (
        db.query(ReviewQueueItem)
        .filter_by(place_id=place_id, field_name=field_name, status="open")
        .order_by(ReviewQueueItem.id.asc())
        .first()
    )


def _confidence_value(field: str, value: object) -> float:
    if field == "description" and value:
        return 0.6
    return 0.85 if value not in (None, "", [], {}) else 0.2


def _payload_hash(payload: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
