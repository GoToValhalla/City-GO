"""
Чтение городов из БД для роутера /cities и связанной логики.
"""

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.city_slug_resolver import resolve_city_by_slug
from services.place_public_visibility import public_place_conditions

PUBLISHED = "published"


# Возвращает список опубликованных городов из базы данных.
def get_cities(db: Session) -> list[City]:
    return db.query(City).filter(City.is_active.is_(True), City.launch_status == PUBLISHED).all()


def get_available_cities(db: Session) -> list[dict[str, object]]:
    """Return the single public city catalogue shared by Web and Telegram.

    A city becomes user-visible only through the explicit admin publication
    action. Channel-specific feature toggles must not make Web and Telegram
    disagree about the available destinations.
    """
    rows = (
        db.query(
            City.slug.label("slug"),
            City.name.label("name"),
            City.country.label("country"),
            City.region.label("region"),
            City.launch_status.label("launch_status"),
            func.count(Place.id).label("places_count"),
        )
        .outerjoin(
            Place,
            and_(
                Place.city_id == City.id,
                *public_place_conditions(),
            ),
        )
        .filter(City.is_active.is_(True), City.launch_status == PUBLISHED)
        .group_by(
            City.id,
            City.slug,
            City.name,
            City.country,
            City.region,
            City.launch_status,
        )
        .order_by(City.name.asc())
        .all()
    )
    return [
        {
            "slug": row.slug,
            "name": row.name,
            "country": row.country,
            "region": row.region,
            "launch_status": row.launch_status,
            "places_count": int(row.places_count or 0),
        }
        for row in rows
    ]

# Возвращает один город по его идентификатору.
def get_city_by_id(db: Session, city_id: int) -> City | None:
    return db.query(City).filter(City.id == city_id).first()


# Возвращает один город по его slug.
def get_city_by_slug(db: Session, slug: str) -> City | None:
    return resolve_city_by_slug(db, slug)


def city_is_published(city: City | None) -> bool:
    return bool(city and city.is_active and city.launch_status == PUBLISHED)