from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places_total


def test_get_places_total_returns_total_with_filters_and_search() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place_1 = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    place_2 = Place(
        title="Coffee House",
        slug="coffee-house",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.96,
        lng=20.49,
    )
    place_3 = Place(
        title="Walk Route",
        slug="walk-route",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 3",
        lat=54.97,
        lng=20.50,
    )
    db.add_all([place_1, place_2, place_3])
    db.commit()

    total = get_places_total(
        db=db,
        city_slug="zelenogradsk",
        q="coffee",
    )

    assert total == 2


def test_get_places_total_returns_zero_for_unknown_city_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    db.add(place)
    db.commit()

    total = get_places_total(
        db=db,
        city_slug="unknown-city",
    )

    assert total == 0