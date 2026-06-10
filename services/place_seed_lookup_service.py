from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.place import Place


def find_city_id(db: Session, city_slug: str) -> int | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    return int(city.id) if city is not None else None


def find_category_id(db: Session, category_code: str) -> int | None:
    category = db.query(Category).filter(Category.code == category_code).first()
    return int(category.id) if category is not None else None


def find_place_by_slug(db: Session, slug: str) -> Place | None:
    return db.query(Place).filter(Place.slug == slug).first()
