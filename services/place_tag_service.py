"""
Связь место ↔ тег (многие ко многим через place_tags).
"""

from sqlalchemy.orm import Session

from models.place_tag import PlaceTag


# Возвращает список всех связей мест и тегов.
def get_place_tags(db: Session) -> list[PlaceTag]:
    return db.query(PlaceTag).all()


# Возвращает список связей по идентификатору места.
def get_place_tags_by_place_id(db: Session, place_id: int) -> list[PlaceTag]:
    return db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()


# Создает новую связь места и тега.
def create_place_tag(db: Session, place_id: int, tag_id: int) -> PlaceTag:
    place_tag = PlaceTag(place_id=place_id, tag_id=tag_id)
    db.add(place_tag)
    db.commit()
    db.refresh(place_tag)
    return place_tag
