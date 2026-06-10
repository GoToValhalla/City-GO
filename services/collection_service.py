"""
Чтение подборок (collections) из БД.
"""

from sqlalchemy.orm import Session

from models.collection import Collection


# Возвращает список активных подборок.
def get_collections(db: Session) -> list[Collection]:
    return (
        db.query(Collection)
        .filter(Collection.is_active.is_(True))
        .order_by(Collection.id.asc())
        .all()
    )


# Возвращает активные подборки по городу.
def get_collections_by_city_id(db: Session, city_id: int) -> list[Collection]:
    return (
        db.query(Collection)
        .filter(Collection.city_id == city_id, Collection.is_active.is_(True))
        .order_by(Collection.id.asc())
        .all()
    )


# Возвращает одну активную подборку по id или None.
def get_collection_by_id(db: Session, collection_id: int) -> Collection | None:
    return (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.is_active.is_(True))
        .first()
    )


# Возвращает одну активную подборку по slug или None.
def get_collection_by_slug(db: Session, slug: str) -> Collection | None:
    return (
        db.query(Collection)
        .filter(Collection.slug == slug, Collection.is_active.is_(True))
        .first()
    )
