from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from models.category import Category  # noqa: F401
from models.city import City
from models.collection import Collection  # noqa: F401
from models.collection_place import CollectionPlace  # noqa: F401
from models.place import Place
from models.place_schedule import PlaceSchedule  # noqa: F401
from models.place_tag import PlaceTag  # noqa: F401
from models.place_verification_task import PlaceVerificationTask
from models.route import Route  # noqa: F401
from models.route_place import RoutePlace  # noqa: F401
from models.tag import Tag  # noqa: F401
from services.place_verification_service import enqueue_stale_places, pending_verification_tasks


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    db.add(City(id=1, slug="zelenogradsk", name="Зеленоградск"))
    db.add(
        Place(
            id=1,
            city_id=1,
            slug="coffee",
            title="Coffee",
            lat=54.96,
            lng=20.48,
            category="cafe",
            last_verified_at=datetime.utcnow() - timedelta(days=31),
        )
    )
    db.commit()
    return db


def test_enqueue_stale_places_creates_pending_task_once() -> None:
    db = _db()
    first = enqueue_stale_places(db, "zelenogradsk")
    second = enqueue_stale_places(db, "zelenogradsk")
    assert first.enqueued == 1
    assert second.already_pending == 1
    assert db.query(PlaceVerificationTask).count() == 1


def test_pending_verification_tasks_returns_pending_items() -> None:
    db = _db()
    enqueue_stale_places(db, "zelenogradsk")
    tasks = pending_verification_tasks(db)
    assert len(tasks) == 1
    assert tasks[0].reason == "stale_data"
