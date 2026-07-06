from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.place_merge_review import PlaceManualOverride
from services.place_lineage import safe_lineage_map, source_priority
from services.place_merge_policy import MIN_CONFIDENCE_GATE


def unsafe_reasons(db: Session, place: Place, changes: dict[str, object], source: str, confidence: float) -> list[str]:
    if confidence < MIN_CONFIDENCE_GATE:
        return ["LOW_CONFIDENCE_SCORE"]
    overrides = {
        row.field_name
        for row in db.query(PlaceManualOverride).filter(
            PlaceManualOverride.place_id == place.id,
            PlaceManualOverride.is_protected.is_(True),
        ).all()
    }
    lineage = safe_lineage_map(place.lineage)
    return [
        reason
        for field, value in changes.items()
        for reason in field_reasons(place, field, value, source, overrides, lineage)
    ]


def field_reasons(place: Place, field: str, value: object, source: str, overrides: set[str], lineage: dict[str, dict[str, object]]) -> list[str]:
    if field in overrides:
        return ["MANUAL_OVERRIDE_PROTECTED"]
    current = getattr(place, field, None)
    current_priority = int((lineage.get(field) or {}).get("priority") or 0)
    if current not in (None, "", {}) and source_priority(source) < current_priority:
        return ["SOURCE_PRIORITY_LOWER"]
    if current not in (None, "", {}) and current != value:
        return ["VALUE_CONFLICT"]
    return []
