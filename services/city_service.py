"""
Чтение городов из БД для роутера /cities и связанной логики.
"""

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.city_slug_resolver import resolve_city_by_slug
from services.feature_toggle_service import is_toggle_enabled
from services.place_public_visibility import public_place_conditions

PUBLISHED = "published"


# Возвращает список опубликованных городов из базы данных.
def get_cities(db: Session) -> list[City]:
    return db.query(City).filter(City.is_active.is_(True), City.launch_status == PUBLISHED).all()


def get_available_cities(db: Session, include_draft: bool = False, *, admin_view: bool = False) -> list[dict[str, object]]:
    if not admin_view and not is_toggle_enabled(db, "web_app_enabled", default=True):
        return []
    query = (
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
        .filter(City.is_active.is_(True))
        .group_by(
            City.id,
            City.slug,
            City.name,
            City.country,
            City.region,
            City.launch_status,
        )
    )

    if not include_draft:
        query = query.filter(City.launch_status == PUBLISHED)

    rows = query.order_by(City.name.asc()).all()

    result: list[dict[str, object]] = []
    for row in rows:
        if not admin_view and not is_toggle_enabled(db, "city_visible_to_users", scope="city", scope_id=row.slug, default=True):
            continue
        if not admin_view and not is_toggle_enabled(db, "web_enabled", scope="city", scope_id=row.slug, default=True):
            continue
        if not admin_view and is_toggle_enabled(db, "admin_only_city", scope="city", scope_id=row.slug, default=False):
            continue
        if not admin_view and is_toggle_enabled(db, "test_city", scope="city", scope_id=row.slug, default=False):
            continue
        result.append({
            "slug": row.slug,
            "name": row.name,
            "country": row.country,
            "region": row.region,
            "launch_status": row.launch_status,
            "places_count": int(row.places_count or 0),
        })
    return result


# Возвращает один город по его идентификатору.
def get_city_by_id(db: Session, city_id: int) -> City | None:
    return db.query(City).filter(City.id == city_id).first()


# Возвращает один город по его slug.
def get_city_by_slug(db: Session, slug: str) -> City | None:
    return resolve_city_by_slug(db, slug)


def city_is_published(city: City | None) -> bool:
    return bool(city and city.is_active and city.launch_status == PUBLISHED)