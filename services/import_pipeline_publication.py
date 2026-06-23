"""Publication decision application for import pipeline."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.place import Place
from services.import_publication_gate import assess_import_quality
from services.review_queue_service import ensure_review_item


def apply_pipeline_publication(db: Session, city: City, job: CityAdminImportJob, place: Place, counters: dict[str, int]) -> None:
    decision = assess_import_quality(title=place.title, lat=place.lat, lng=place.lng, category=place.category,
                                     confidence=place.confidence, source=place.source, address=place.address,
                                     opening_hours=place.opening_hours)
    _apply_decision(place, decision.decision, decision.reason, decision.is_route_eligible)
    counters[_counter_key(place.publication_status, place.is_route_eligible)] += 1
    if place.publication_status == "needs_review":
        ensure_review_item(db, city_id=city.id, place_id=place.id, job_id=job.id, field_name=_review_field(decision.reason), reason=decision.reason)


def _apply_decision(place: Place, decision: str, reason: str, route_eligible: bool) -> None:
    if reason in {"no_coordinates", "hidden_category"}:
        _set_visibility(place, "archived", active=False, published=False, catalog=False, route=False)
    elif decision == "auto_publish":
        _set_visibility(place, "published", active=True, published=True, catalog=True, route=route_eligible)
    else:
        _set_visibility(place, "needs_review", active=True, published=False, catalog=False, route=False)


def _set_visibility(place: Place, status: str, *, active: bool, published: bool, catalog: bool, route: bool) -> None:
    place.publication_status = status
    place.is_active = active
    place.is_published = published
    place.is_visible_in_catalog = catalog
    place.is_searchable = published
    place.is_route_eligible = route


def _counter_key(status: str, route_eligible: bool) -> str:
    if status == "published":
        return "auto_published" if route_eligible else "limited_published"
    return {"archived": "rejected", "hidden": "rejected"}.get(status, "review_required")


def _review_field(reason: str) -> str:
    return {
        "non_tourist_category": "category",
        "low_confidence": "confidence",
        "missing_hours_for_dynamic_category": "opening_hours",
        "no_source": "source",
    }.get(reason, "publication_status")
