"""
Чтение подборок (collections) из БД.
"""

from sqlalchemy.orm import Session

from models.city import City
from models.collection import Collection


def _public_collections_query(db: Session):
    return (
        db.query(Collection)
        .join(City, Collection.city_id == City.id)
        .filter(
            Collection.is_active.is_(True),
            City.is_active.is_(True),
            City.launch_status == "published",
        )
    )


# Возвращает список активных подборок.
def get_collections(db: Session) -> list[Collection]:
    return _public_collections_query(db).order_by(Collection.id.asc()).all()


# Возвращает активные подборки по городу.
def get_collections_by_city_id(db: Session, city_id: int) -> list[Collection]:
    return (
        _public_collections_query(db)
        .filter(Collection.city_id == city_id)
        .order_by(Collection.id.asc())
        .all()
    )


# Возвращает одну активную подборку по id или None.
def get_collection_by_id(db: Session, collection_id: int) -> Collection | None:
    return _public_collections_query(db).filter(Collection.id == collection_id).first()


# Возвращает одну активную подборку по slug или None.
def get_collection_by_slug(db: Session, slug: str) -> Collection | None:
    return _public_collections_query(db).filter(Collection.slug == slug).first()
