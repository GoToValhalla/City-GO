"""
Позиции мест внутри подборки (collection_places).
"""

from sqlalchemy.orm import Session

from models.collection_place import CollectionPlace


# Возвращает список всех связей подборок и мест.
def get_collection_places(db: Session) -> list[CollectionPlace]:
    return db.query(CollectionPlace).all()


# Возвращает список связей по идентификатору подборки.
def get_collection_places_by_collection_id(
    db: Session,
    collection_id: int,
) -> list[CollectionPlace]:
    return (
        db.query(CollectionPlace)
        .filter(CollectionPlace.collection_id == collection_id)
        .order_by(CollectionPlace.position.asc())
        .all()
    )
