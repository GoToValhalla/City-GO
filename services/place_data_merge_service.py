from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models.data_foundation import EnrichmentTask
from models.place import Place
from models.place_merge_review import ReviewItem
from services.place_cache_invalidation import invalidate_place_cache
from services.place_data_sanitizer import sanitize_change
from services.place_lineage import lineage_entry, safe_lineage_map
from services.place_merge_audit import add_place_audit
from services.place_merge_db import get_place, get_review, protect_fields
from services.place_merge_errors import PlaceMergeError
from services.place_merge_policy import is_service_only_category, normalize_changes
from services.place_merge_safety import unsafe_reasons


class PlaceDataMergeService:
    def merge_from_enrichment_task(self, db: Session, task_id: int, actor: str = "system") -> dict[str, object]:
        task = db.get(EnrichmentTask, task_id)
        if task is None or task.place_id is None:
            raise PlaceMergeError("TASK_NOT_FOUND", "Задача обогащения не найдена")
        payload = task.payload or {}
        changes = payload.get("changes") if isinstance(payload.get("changes"), dict) else payload
        return self.apply_safe(db, task.place_id, changes, str(payload.get("source") or task.task_type), float(payload.get("confidence") or 1.0), actor, task.id)

    def apply_safe(self, db: Session, place_id: int, changes: dict[str, object], source: str, confidence: float, actor: str, task_id: int | None = None) -> dict[str, object]:
        place = get_place(db, place_id)
        normalized = self._sanitized_changes(changes)
        if not normalized:
            return {"status": "skipped", "place_id": place_id, "reason": "no_safe_changes"}
        reasons = unsafe_reasons(db, place, normalized, source, confidence)
        if reasons:
            review = self.create_review_item(db, place, normalized, source, confidence, ",".join(sorted(set(reasons))), task_id, actor)
            return {"status": "review_required", "review_id": review.id, "reason": review.reason}
        self._apply_update(db, place, normalized, source, confidence, actor, "merge_auto_apply")
        return {"status": "applied", "place_id": place_id, "version": place.version + 1}

    def create_review_item(self, db: Session, place: Place, changes: dict[str, object], source: str, confidence: float, reason: str, task_id: int | None, actor: str) -> ReviewItem:
        diff = {field: {"current": getattr(place, field, None), "proposed": value, "reason": reason} for field, value in changes.items()}
        item = ReviewItem(place_id=place.id, enrichment_task_id=task_id, proposed_diff=diff, status="pending", created_by=actor, place_version_at_creation=place.version, source=source, confidence=confidence, reason=reason)
        db.add(item)
        add_place_audit(db, actor, "place_merge_review_created", place.id, None, {"review_id": item.id, "reason": reason}, reason)
        db.commit()
        db.refresh(item)
        return item

    def apply_review_item(self, db: Session, review_id: int, fields: list[str], actor: str, expected_version: int, force_override_protected: bool = False) -> ReviewItem:
        item = get_review(db, review_id)
        if item.status != "pending":
            raise PlaceMergeError("REVIEW_ALREADY_CLOSED", "Заявка уже закрыта")
        place = get_place(db, item.place_id)
        if place.version != expected_version or place.version != item.place_version_at_creation:
            raise PlaceMergeError("VERSION_MISMATCH", "Данные места изменились, обновите diff")
        diff = item.proposed_diff or {}
        changes = {field: diff[field]["proposed"] for field in fields if field in diff}
        if not changes:
            raise PlaceMergeError("NO_FIELDS_SELECTED", "Выберите поля для применения")
        self._apply_update(db, place, changes, item.source or "MANUAL", item.confidence or 1.0, actor, "place_merge_review_applied")
        protect_fields(db, place.id, changes, actor, force_override_protected)
        item.status, item.reviewed_by, item.reviewed_at = "approved", actor, datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
        return item

    def reject_review_item(self, db: Session, review_id: int, actor: str, reason: str) -> ReviewItem:
        item = get_review(db, review_id)
        if item.status != "pending":
            raise PlaceMergeError("REVIEW_ALREADY_CLOSED", "Заявка уже закрыта")
        item.status, item.reviewed_by, item.reviewed_at = "rejected", actor, datetime.now(timezone.utc)
        add_place_audit(db, actor, "place_merge_review_rejected", item.place_id, item.proposed_diff, None, reason)
        db.commit()
        db.refresh(item)
        return item

    def _apply_update(self, db: Session, place: Place, changes: dict[str, object], source: str, confidence: float, actor: str, action: str) -> None:
        values = self._service_only_values(changes) | changes
        lineage = safe_lineage_map(place.lineage) | {field: lineage_entry(source, confidence) for field in values}
        values |= {"lineage": lineage, "version": place.version + 1, "last_enriched_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
        updated = db.query(Place).filter(Place.id == place.id, Place.version == place.version).update(values)
        if updated != 1:
            raise PlaceMergeError("VERSION_MISMATCH", "Данные места изменились, обновите diff")
        add_place_audit(db, actor, action, place.id, None, values, None)
        invalidate_place_cache(place.id)
        db.commit()

    def _sanitized_changes(self, changes: dict[str, object]) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        for field, value in normalize_changes(changes).items():
            try:
                sanitized[field] = sanitize_change(field, value)
            except ValueError as exc:
                if str(exc) == "PLACEHOLDER_VALUE":
                    continue
                raise
        return sanitized

    def _service_only_values(self, changes: dict[str, object]) -> dict[str, object]:
        category = changes.get("canonical_category") or changes.get("category")
        return {"is_published": False, "is_visible_in_catalog": False, "is_route_eligible": False, "internal_status": "service_only"} if is_service_only_category(category) else {}
