from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.place_merge_review import PlaceManualOverride, ReviewItem
from services.place_merge_errors import PlaceMergeError


def get_place(db: Session, place_id: int) -> Place:
    place = db.get(Place, place_id)
    if place is None:
        raise PlaceMergeError("PLACE_NOT_FOUND", "Место не найдено")
    return place


def get_review(db: Session, review_id: int) -> ReviewItem:
    item = db.get(ReviewItem, review_id)
    if item is None:
        raise PlaceMergeError("REVIEW_NOT_FOUND", "Заявка не найдена")
    return item


def protect_fields(db: Session, place_id: int, changes: dict[str, object], actor: str, force: bool) -> None:
    for field, value in changes.items():
        db.add(PlaceManualOverride(
            place_id=place_id,
            field_name=field,
            is_protected=not force,
            override_value={"value": value},
            set_by=actor,
        ))
