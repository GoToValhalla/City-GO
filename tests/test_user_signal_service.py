from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.base import Base
from models.category import Category  # noqa: F401
from models.city import City  # noqa: F401
from models.collection import Collection  # noqa: F401
from models.collection_place import CollectionPlace  # noqa: F401
from models.place import Place  # noqa: F401
from models.place_schedule import PlaceSchedule  # noqa: F401
from models.place_tag import PlaceTag  # noqa: F401
from models.route import Route  # noqa: F401
from models.route_place import RoutePlace  # noqa: F401
from models.tag import Tag  # noqa: F401
from models.user_signal import UserSignal
from schemas.user_signal import UserSignalCreate
from services.user_profile_from_signals_service import build_user_profile_from_signals
from services.user_signal_service import create_user_signal, derive_user_profile, summarize_user_signals


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine, tables=[UserSignal.__table__])
    return sessionmaker(bind=engine)()


def _payload(signal_type: str) -> UserSignalCreate:
    return UserSignalCreate(
        user_id="u1",
        signal_type=signal_type,
        entity_type="place",
        entity_id="p1",
        payload={"source": "test", "category": "coffee"},
    )


def _route_payload(signal_type: str) -> UserSignalCreate:
    return UserSignalCreate(
        user_id="u1",
        signal_type=signal_type,
        entity_type="route",
        entity_id="r1",
        payload={"source": "test"},
    )


def test_create_user_signal_persists_event() -> None:
    db = _db()
    signal = create_user_signal(db, _payload("view_place"))
    assert signal.id == 1
    assert db.query(UserSignal).count() == 1


def test_summarize_user_signals_counts_signal_and_entity_types() -> None:
    db = _db()
    create_user_signal(db, _payload("view_place"))
    create_user_signal(db, _payload("save_place"))
    summary = summarize_user_signals(db, "u1")
    assert summary.total == 2
    assert summary.by_signal_type == {"view_place": 1, "save_place": 1}
    assert summary.by_entity_type == {"place": 2}


def test_derive_user_profile_counts_categories_and_actions() -> None:
    db = _db()
    create_user_signal(db, _payload("view_place"))
    create_user_signal(db, _payload("save_place"))
    profile = derive_user_profile(db, "u1")
    assert profile.total_signals == 2
    assert profile.preferred_categories == {"coffee": 2}
    assert profile.action_counts == {"view_place": 1, "save_place": 1}
    assert profile.last_activity_at is not None


def test_derive_user_profile_collects_personalization_signals() -> None:
    db = _db()
    create_user_signal(db, _payload("favorite_place"))
    create_user_signal(db, _payload("like_place"))
    create_user_signal(db, _payload("dislike_place"))
    create_user_signal(db, _payload("visited_place"))
    create_user_signal(db, _route_payload("completed_route"))
    profile = derive_user_profile(db, "u1")
    assert profile.favorite_place_ids == ["p1"]
    assert profile.liked_place_ids == ["p1"]
    assert profile.disliked_place_ids == ["p1"]
    assert profile.visited_place_ids == ["p1"]
    assert profile.completed_routes_count == 1


def test_build_user_profile_from_signals_maps_to_recommendation_profile() -> None:
    db = _db()
    create_user_signal(db, _payload("like_place"))
    create_user_signal(db, _payload("visited_place"))
    profile = build_user_profile_from_signals(db, "u1")
    assert profile is not None
    assert profile.preferences.interests == ["coffee"]
    assert profile.history.liked_place_ids == ["p1"]
    assert profile.history.visited_place_ids == ["p1"]
    assert profile.behavior.category_affinity == {"coffee": 1.0}
