from sqlalchemy.orm import Session

from schemas.user_profile import UserBehaviorProfile, UserHistory, UserProfile, UserStaticPreferences
from services.user_signal_service import derive_user_profile


def build_user_profile_from_signals(db: Session, user_id: str | None) -> UserProfile | None:
    if user_id is None:
        return None
    derived = derive_user_profile(db, user_id)
    return UserProfile(
        preferences=UserStaticPreferences(interests=_top_categories(derived.preferred_categories)),
        history=UserHistory(
            visited_place_ids=derived.visited_place_ids,
            liked_place_ids=derived.liked_place_ids,
            disliked_place_ids=derived.disliked_place_ids,
        ),
        behavior=UserBehaviorProfile(
            category_affinity=_category_affinity(derived.preferred_categories),
            completed_routes_count=derived.completed_routes_count,
            total_sessions_count=derived.total_signals,
            last_active_date=derived.last_activity_at,
        ),
    )


def _top_categories(counts: dict[str, int]) -> list[str]:
    ranked = sorted(counts.items(), key=lambda item: item[1], reverse=True)
    return list(map(lambda item: item[0], ranked[:5]))


def _category_affinity(counts: dict[str, int]) -> dict[str, float]:
    max_count = max(counts.values(), default=0)
    if max_count <= 0:
        return {}
    return dict(map(lambda item: (item[0], round(item[1] / max_count, 3)), counts.items()))
