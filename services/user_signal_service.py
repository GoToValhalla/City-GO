from functools import reduce

from sqlalchemy.orm import Session

from models.user_signal import UserSignal
from schemas.user_signal import (
    NEGATIVE_PLACE_SIGNALS,
    POSITIVE_PLACE_SIGNALS,
    SIGNAL_FAVORITE_PLACE,
    SIGNAL_COMPLETED_ROUTE,
    VISIT_PLACE_SIGNALS,
    UserDerivedProfile,
    UserSignalCreate,
    UserSignalSummary,
)


def create_user_signal(db: Session, payload: UserSignalCreate) -> UserSignal:
    signal = UserSignal(**payload.model_dump())
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


def summarize_user_signals(db: Session, user_id: str) -> UserSignalSummary:
    signals = db.query(UserSignal).filter(UserSignal.user_id == user_id).all()
    return UserSignalSummary(
        user_id=user_id,
        total=len(signals),
        by_signal_type=reduce(
            lambda counts, signal: _count(counts, signal.signal_type),
            signals,
            {},
        ),
        by_entity_type=reduce(
            lambda counts, signal: _count(counts, signal.entity_type),
            signals,
            {},
        ),
    )


def derive_user_profile(db: Session, user_id: str) -> UserDerivedProfile:
    signals = db.query(UserSignal).filter(UserSignal.user_id == user_id).all()
    return UserDerivedProfile(
        user_id=user_id,
        total_signals=len(signals),
        preferred_categories=reduce(_count_category, signals, {}),
        action_counts=reduce(lambda counts, signal: _count(counts, signal.signal_type), signals, {}),
        favorite_place_ids=_place_ids(signals, {SIGNAL_FAVORITE_PLACE}),
        liked_place_ids=_place_ids(signals, POSITIVE_PLACE_SIGNALS),
        disliked_place_ids=_place_ids(signals, NEGATIVE_PLACE_SIGNALS),
        visited_place_ids=_place_ids(signals, VISIT_PLACE_SIGNALS),
        completed_routes_count=sum(map(_is_completed_route, signals)),
        last_activity_at=max(map(lambda signal: signal.created_at, signals), default=None),
    )


def _count(counts: dict[str, int], key: str) -> dict[str, int]:
    return {**counts, key: counts.get(key, 0) + 1}


def _count_category(counts: dict[str, int], signal: UserSignal) -> dict[str, int]:
    payload = signal.payload if isinstance(signal.payload, dict) else {}
    category = payload.get("category")
    return _count(counts, category) if isinstance(category, str) and category else counts


def _place_ids(signals: list[UserSignal], signal_types: frozenset[str] | set[str]) -> list[str]:
    matched = filter(lambda signal: _matches_place_signal(signal, signal_types), signals)
    return sorted(set(map(lambda signal: str(signal.entity_id), matched)))


def _matches_place_signal(signal: UserSignal, signal_types: frozenset[str] | set[str]) -> bool:
    return signal.entity_type == "place" and signal.signal_type in signal_types


def _is_completed_route(signal: UserSignal) -> int:
    return 1 if signal.entity_type == "route" and signal.signal_type == SIGNAL_COMPLETED_ROUTE else 0
