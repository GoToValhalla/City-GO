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
from schemas.sorting import SortingParams
from services.place_sorting_service import apply_place_sorting


def test_apply_place_sorting_by_title_asc() -> None:
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

    db.add_all(
        [
            Place(
                title="Bravo",
                slug="bravo",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 1",
                lat=54.95,
                lng=20.48,
            ),
            Place(
                title="Alpha",
                slug="alpha",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 2",
                lat=54.96,
                lng=20.49,
            ),
        ]
    )
    db.commit()

    query = db.query(Place)
    sorted_query = apply_place_sorting(
        query,
        SortingParams(sort_by="title", sort_order="asc"),
    )
    items = sorted_query.all()

    assert len(items) == 2
    assert items[0].title == "Alpha"
    assert items[1].title == "Bravo"


def test_apply_place_sorting_by_title_desc() -> None:
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

    db.add_all(
        [
            Place(
                title="Bravo",
                slug="bravo",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 1",
                lat=54.95,
                lng=20.48,
            ),
            Place(
                title="Alpha",
                slug="alpha",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 2",
                lat=54.96,
                lng=20.49,
            ),
        ]
    )
    db.commit()

    query = db.query(Place)
    sorted_query = apply_place_sorting(
        query,
        SortingParams(sort_by="title", sort_order="desc"),
    )
    items = sorted_query.all()

    assert len(items) == 2
    assert items[0].title == "Bravo"
    assert items[1].title == "Alpha"