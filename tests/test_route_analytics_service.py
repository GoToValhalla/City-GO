from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.category import Category  # noqa: F401
from models.city import City  # noqa: F401
from models.collection import Collection  # noqa: F401
from models.collection_place import CollectionPlace  # noqa: F401
from models.place import Place  # noqa: F401
from models.place_schedule import PlaceSchedule  # noqa: F401
from models.place_tag import PlaceTag  # noqa: F401
from models.route import Route  # noqa: F401
from models.route_build_event import RouteBuildEvent  # noqa: F401
from models.route_place import RoutePlace  # noqa: F401
from models.tag import Tag  # noqa: F401
from services.route_analytics_service import record_route_build, route_analytics_summary
from services.user_route_history_service import user_route_history


def _db():
    engine = create_engine("sqlite:///:memory:")
    RouteBuildEvent.__table__.create(bind=engine)
    return sessionmaker(bind=engine)()


def _route(route_id: str, quality: float, warnings: list[str]):
    return SimpleNamespace(
        route_id=route_id,
        total_places=2,
        total_minutes=45,
        quality_score=quality,
        warning_count=len(warnings),
        has_warnings=bool(warnings),
        warnings=warnings,
        quality_breakdown={"score": quality},
    )


def test_record_route_build_persists_metrics() -> None:
    db = _db()
    saved = record_route_build(
        db,
        _route("r1", 0.8, ["warning"]),
        source="recommendations",
        latency_ms=123,
        city_id="zelenogradsk",
        user_id="u1",
    )
    event = db.query(RouteBuildEvent).one()
    assert saved is True
    assert event.route_id == "r1"
    assert event.user_id == "u1"
    assert event.quality_score == 0.8
    assert event.warning_count == 1


def test_route_analytics_summary_aggregates_events() -> None:
    db = _db()
    record_route_build(db, _route("r1", 0.8, []), source="api", latency_ms=100)
    record_route_build(db, _route("r2", 0.4, ["w"]), source="api", latency_ms=200)
    summary = route_analytics_summary(db)
    assert summary["total_routes"] == 2
    assert summary["average_quality_score"] == 0.6
    assert summary["warning_rate"] == 0.5
    assert summary["by_source"] == {"api": 2}


def test_user_route_history_returns_recent_user_events() -> None:
    db = _db()
    record_route_build(db, _route("r1", 0.8, []), source="api", latency_ms=100, user_id="u1")
    record_route_build(db, _route("r2", 0.7, []), source="api", latency_ms=100, user_id="u2")
    history = user_route_history(db, "u1")
    assert len(history) == 1
    assert history[0]["route_id"] == "r1"
