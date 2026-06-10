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
from services.place_service import get_places


def test_get_places_applies_limit_and_offset() -> None:
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

    places = [
        Place(
            title=f"Place {index}",
            slug=f"place-{index}",
            city_id=1,
            category_id=1,
            category="coffee",
            address=f"Addr {index}",
            lat=54.95 + index / 1000,
            lng=20.48 + index / 1000,
        )
        for index in range(1, 6)
    ]
    db.add_all(places)
    db.commit()

    items = get_places(db=db, limit=2, offset=2)

    assert len(items) == 2
    assert items[0].slug == "place-3"
    assert items[1].slug == "place-4"