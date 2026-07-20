"""
Позиции мест внутри подборки (collection_places).
"""

from sqlalchemy.orm import Session

from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from services.place_public_visibility import public_place_conditions


def _public_collection_places_query(db: Session):
    return (
        db.query(CollectionPlace)
        .join(Collection, CollectionPlace.collection_id == Collection.id)
        .join(City, Collection.city_id == City.id)
        .join(Place, CollectionPlace.place_id == Place.id)
        .filter(
            Collection.is_active.is_(True),
            City.is_active.is_(True),
            City.launch_status == "published",
            *public_place_conditions(),
        )
    )


# Возвращает список всех связей подборок и мест.
def get_collection_places(db: Session) -> list[CollectionPlace]:
    return _public_collection_places_query(db).order_by(CollectionPlace.position.asc()).all()


# Возвращает список связей по идентификатору подборки.
def get_collection_places_by_collection_id(
    db: Session,
    collection_id: int,
) -> list[CollectionPlace]:
    return (
        _public_collection_places_query(db)
        .filter(CollectionPlace.collection_id == collection_id)
        .order_by(CollectionPlace.position.asc())
        .all()
    )
