from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection  # noqa: F401
from models.collection_place import CollectionPlace  # noqa: F401
from models.place import Place
from models.place_import_event import PlaceImportEvent
from models.place_schedule import PlaceSchedule  # noqa: F401
from models.place_tag import PlaceTag  # noqa: F401
from models.route import Route  # noqa: F401
from models.route_place import RoutePlace  # noqa: F401
from models.tag import Tag  # noqa: F401
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_import_service import import_place_seed_items


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(City(id=1, slug="zelenogradsk", name="Зеленоградск"))
    session.add(Category(id=2, code="coffee", name="Кофе"))
    session.commit()
    return session


def _item(slug: str = "coffee-place") -> PlaceSeedItem:
    return PlaceSeedItem(
        title="Coffee Place",
        slug=slug,
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee"),
        lat=54.96,
        lng=20.48,
        opening_hours={"mon": {"open": "09:00", "close": "18:00"}},
        average_visit_duration_minutes=30,
        price_level=2,
        last_verified_at="2026-06-04",
    )


def test_import_place_seed_items_dry_run_counts_create_without_write() -> None:
    db = _db()
    result = import_place_seed_items(db, [_item()], dry_run=True)
    assert result.created == 1
    assert db.query(Place).count() == 0
    assert db.query(PlaceImportEvent).count() == 1


def test_import_place_seed_items_writes_and_updates_by_slug() -> None:
    db = _db()
    created = import_place_seed_items(db, [_item()], dry_run=False)
    updated = import_place_seed_items(db, [_item()], dry_run=False)
    place = db.query(Place).filter(Place.slug == "coffee-place").first()
    assert created.created == 1
    assert updated.updated == 1
    assert db.query(PlaceImportEvent).count() == 2
    assert place is not None
    assert place.city_id == 1
    assert place.opening_hours == {"mon": {"open": "09:00", "close": "18:00"}}
    assert place.average_visit_duration_minutes == 30
    assert place.price_level == 2
    assert place.last_verified_at is not None


def test_import_place_seed_items_dry_run_does_not_touch_existing_place_new() -> None:
    db = _db()
    import_place_seed_items(db, [_item()], dry_run=False)
    place = db.query(Place).filter(Place.slug == "coffee-place").first()
    original_updated_at = place.updated_at
    original_title = place.title

    changed_item = _item().model_copy(update={"title": "Changed Title Dry Run"})
    result = import_place_seed_items(db, [changed_item], dry_run=True)

    db.refresh(place)
    assert result.updated == 1
    assert place.title == original_title
    assert place.updated_at == original_updated_at
    assert db.query(Place).count() == 1


def test_import_place_seed_items_reports_duplicate_slug() -> None:
    db = _db()
    result = import_place_seed_items(db, [_item(), _item()], dry_run=True)
    assert result.skipped == 1
    assert "duplicate slug" in result.errors[0]


def test_import_place_seed_items_reports_unknown_city() -> None:
    db = _db()
    item = _item().model_copy(update={"city_slug": "unknown"})
    result = import_place_seed_items(db, [item], dry_run=True)
    assert result.invalid == 1
    assert "unknown city_slug" in result.errors[0]
