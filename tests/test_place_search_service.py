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


def test_get_places_filters_by_q_on_title_and_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
        launch_status="published",
        is_active=True,
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
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
    )
    place_2 = Place(
        title="Walk Route",
        slug="walk-route",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.96,
        lng=20.49,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
    )
    db.add_all([place_1, place_2])
    db.commit()

    items = get_places(db=db, q="coffee")

    assert len(items) == 1
    assert items[0].slug == "coffee-point"
