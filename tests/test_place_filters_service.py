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
from services.place_filters_service import apply_place_filters


def test_apply_place_filters_by_city_slug_returns_filtered_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    tag = Tag(id=1, code="pet_friendly", name="Pet Friendly")
    city_1 = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
        launch_status="published",
        is_active=True,
    )
    city_2 = City(
        id=2,
        name="Kaliningrad",
        slug="kaliningrad",
        launch_status="published",
        is_active=True,
    )
    db.add_all([category, tag, city_1, city_2])
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
        city_id=2,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.71,
        lng=20.51,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
    )
    db.add_all([place_1, place_2])
    db.commit()

    query = db.query(Place)
    filtered_query = apply_place_filters(
        query=query,
        city_id=None,
        city_slug="zelenogradsk",
        category_id=None,
        tag_id=None,
        db=db,
    )

    assert filtered_query is not None

    items = filtered_query.all()
    assert len(items) == 1
    assert items[0].slug == "coffee-point"


def test_apply_place_filters_returns_none_for_unknown_city_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    tag = Tag(id=1, code="pet_friendly", name="Pet Friendly")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
        launch_status="published",
        is_active=True,
    )
    db.add_all([category, tag, city])
    db.commit()

    query = db.query(Place)
    filtered_query = apply_place_filters(
        query=query,
        city_id=None,
        city_slug="unknown-city",
        category_id=None,
        tag_id=None,
        db=db,
    )

    assert filtered_query is None
