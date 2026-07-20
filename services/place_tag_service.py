"""
Связь место ↔ тег (многие ко многим через place_tags).
"""

from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from services.place_public_visibility import apply_public_place_visibility, public_place_conditions


# Возвращает список всех связей мест и тегов.
def get_place_tags(db: Session) -> list[PlaceTag]:
    return (
        db.query(PlaceTag)
        .join(Place, PlaceTag.place_id == Place.id)
        .filter(*public_place_conditions())
        .all()
    )


# Возвращает список связей по идентификатору места.
def get_place_tags_by_place_id(db: Session, place_id: int) -> list[PlaceTag]:
    visible = apply_public_place_visibility(db.query(Place).filter(Place.id == place_id)).first()
    if visible is None:
        return []
    return db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()


# Создает новую связь места и тега.
def create_place_tag(db: Session, place_id: int, tag_id: int) -> PlaceTag:
    place_tag = PlaceTag(place_id=place_id, tag_id=tag_id)
    db.add(place_tag)
    db.commit()
    db.refresh(place_tag)
    return place_tag


# Создает новую связь места и тега.
def create_place_tag(db: Session, place_id: int, tag_id: int) -> PlaceTag:
    place_tag = PlaceTag(place_id=place_id, tag_id=tag_id)
    db.add(place_tag)
    db.commit()
    db.refresh(place_tag)
    return place_tag
