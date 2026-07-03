"""
Чтение городов из БД для роутера /cities и связанной логики.

City selector counters describe the published catalogue, not the stricter tourist-route candidate pool.
"""

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, object_session

from models.city import City
from models.place import Place
from services.city_slug_resolver import resolve_city_by_slug
from services.feature_toggle_service import is_toggle_enabled

PUBLISHED = "published"
PUBLIC_ACTIVE_STATUS = "active"
PUBLICATION_STATUSES = ("published", "auto_published", "limited_published")


# Возвращает список опубликованных городов из базы данных.
def get_cities(db: Session) -> list[City]:
    return [city for city in db.query(City).filter(City.is_active.is_(True), City.launch_status == PUBLISHED).all() if _city_visible_to_users(db, city.slug)]


def get_available_cities(db: Session, *, include_draft: bool = False) -> list[dict[str, object]]:
    """Return the public city catalogue shared by Web and Telegram."""
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
                *_catalog_counter_place_conditions(),
            ),
        )
        .filter(City.is_active.is_(True))
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
    if not include_draft:
        rows = [row for row in rows if row.launch_status == PUBLISHED]
    rows = [row for row in rows if _city_visible_to_users(db, row.slug)]
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
    return bool(city and city.is_active and city.launch_status == PUBLISHED and _city_visible_to_users_for_city(city))


def _catalog_counter_place_conditions() -> tuple[object, ...]:
    """Count published catalogue places without applying the route eligibility gate."""
    return (
        Place.is_active.is_(True),
        or_(Place.status.is_(None), Place.status == PUBLIC_ACTIVE_STATUS),
        Place.is_published.is_(True),
        Place.is_visible_in_catalog.is_(True),
        or_(Place.publication_status.is_(None), Place.publication_status.in_(PUBLICATION_STATUSES)),
    )


def _city_visible_to_users(db: Session, city_slug: str) -> bool:
    if is_toggle_enabled(db, "admin_only_city", scope="city", scope_id=city_slug, default=False):
        return False
    if is_toggle_enabled(db, "test_city", scope="city", scope_id=city_slug, default=False):
        return False
    return True


def _city_visible_to_users_for_city(city: City) -> bool:
    db = object_session(city)
    if db is None:
        return True
    return _city_visible_to_users(db, city.slug)
