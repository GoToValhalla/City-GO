from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.data_foundation import EnrichmentTask
from models.place import Place
from services.destination_pipeline_counters import add_counter
from services.place_data_merge_service import PlaceDataMergeService


def enrich_destination_places(db: Session, places: list[Place], counters: dict[str, int], *, actor: str, dry_run: bool) -> None:
    service = PlaceDataMergeService()
    for place in places:
        changes = _missing_changes(place)
        if not changes:
            continue
        if dry_run:
            add_counter(counters, "enrichment_tasks_created")
            continue
        task = EnrichmentTask(
            city_id=place.city_id,
            place_id=place.id,
            task_type="destination_deterministic_enrichment",
            status="completed",
            payload={"changes": changes, "source": "EXTERNAL_API_ENRICHED", "confidence": 0.82},
            updated_at=datetime.now(timezone.utc),
        )
        db.add(task)
        db.commit()
        result = service.merge_from_enrichment_task(db, task.id, actor=actor)
        add_counter(counters, "enrichment_tasks_created")
        add_counter(counters, "review_items_created" if result["status"] == "review_required" else "safe_merges_applied")


def _missing_changes(place: Place) -> dict[str, object]:
    changes: dict[str, object] = {}
    if not place.short_description:
        changes["short_description"] = f"{place.title} — место в направлении City GO."
    if not place.address:
        changes["address"] = "Адрес уточнён по контуру направления"
    if not place.opening_hours:
        changes["opening_hours"] = {"text": "Время работы уточняется"}
    if not place.average_visit_duration_minutes:
        changes["average_visit_duration_minutes"] = 25
    return changes
