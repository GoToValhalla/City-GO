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
from models.route import Route  # noqa: F401
from models.route_place import RoutePlace  # noqa: F401
from models.tag import Tag  # noqa: F401
from services.place_coverage_service import build_place_coverage_report


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(City(id=1, slug="zelenogradsk", name="Зеленоградск"))
    session.add(
        Place(
            city_id=1,
            slug="coffee",
            title="Coffee",
            lat=54.96,
            lng=20.48,
            category="coffee",
            opening_hours={"mon": {"open": "10:00", "close": "20:00"}},
            average_visit_duration_minutes=30,
            source="osm",
            confidence=0.8,
        )
    )
    session.commit()
    return session


def test_build_place_coverage_report_counts_quality_fields() -> None:
    report = build_place_coverage_report(_db(), "zelenogradsk")
    assert report.total_places == 1
    assert report.with_coordinates == 1
    assert report.with_opening_hours == 1
    assert report.with_visit_duration == 1
    assert report.with_source == 1
    assert report.active_places == 1
    assert report.needs_verification == 0
    assert report.closed_places == 0
    assert report.average_confidence == 0.8
    assert report.category_counts == {"coffee": 1}
    assert "food" in report.missing_required_categories
    assert report.route_ready_score > 0


def test_build_place_coverage_report_handles_unknown_city() -> None:
    report = build_place_coverage_report(_db(), "unknown")
    assert report.total_places == 0
    assert report.route_ready_score == 0.0


def test_build_place_coverage_report_counts_stale_status() -> None:
    db = _db()
    db.add(
        Place(
            city_id=1,
            slug="old",
            title="Old",
            lat=54.97,
            lng=20.49,
            category="cafe",
            last_verified_at=datetime.utcnow() - timedelta(days=31),
        )
    )
    db.commit()
    report = build_place_coverage_report(db, "zelenogradsk")
    assert report.active_places == 1
    assert report.needs_verification == 1
from datetime import datetime, timedelta
