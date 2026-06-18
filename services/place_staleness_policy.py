from __future__ import annotations

from datetime import datetime, timedelta

PLACE_STATUS_ACTIVE = "active"
PLACE_STATUS_NEEDS_VERIFICATION = "needs_verification"
PLACE_STATUS_TEMPORARILY_CLOSED = "temporarily_closed"
PLACE_STATUS_CLOSED = "closed"
PLACE_STATUS_VALUES = (
    PLACE_STATUS_ACTIVE,
    PLACE_STATUS_NEEDS_VERIFICATION,
    PLACE_STATUS_TEMPORARILY_CLOSED,
    PLACE_STATUS_CLOSED,
)
DYNAMIC_STALE_AFTER_DAYS = 30
STATIC_STALE_AFTER_DAYS = 90
STALE_STRONG_AFTER_DAYS = 60
DYNAMIC_CATEGORIES = frozenset({"bar", "cafe", "coffee", "food", "restaurant"})
STATIC_CATEGORIES = frozenset({"museum", "park", "walk", "sight", "culture"})


def normalize_place_status(value: str | None) -> str:
    return value if value in PLACE_STATUS_VALUES else PLACE_STATUS_ACTIVE


def effective_place_status(place: object, now: datetime | None = None) -> str:
    status = normalize_place_status(str(getattr(place, "status", "") or ""))
    if status in (PLACE_STATUS_CLOSED, PLACE_STATUS_TEMPORARILY_CLOSED):
        return status
    if _is_stale(place, now or datetime.utcnow()):
        return PLACE_STATUS_NEEDS_VERIFICATION
    return status


def is_route_usable_place(place: object) -> bool:
    # Legacy imported places can have is_active=NULL. In SQL visibility NULL is already
    # treated as public/active; the in-memory hard filter must follow the same contract.
    raw_active = getattr(place, "is_active", True)
    active = True if raw_active is None else bool(raw_active)
    status = normalize_place_status(str(getattr(place, "status", "") or ""))
    return active and status not in (PLACE_STATUS_CLOSED, PLACE_STATUS_TEMPORARILY_CLOSED)


def is_needs_verification(place: object, now: datetime | None = None) -> bool:
    return effective_place_status(place, now) == PLACE_STATUS_NEEDS_VERIFICATION


def staleness_penalty(place: object, now: datetime | None = None) -> float:
    if not is_needs_verification(place, now):
        return 0.0
    value = getattr(place, "last_verified_at", None)
    if not isinstance(value, datetime):
        return 0.1
    age_days = ((now or datetime.utcnow()) - value).days
    return 0.2 if _is_dynamic(place) and age_days > STALE_STRONG_AFTER_DAYS else 0.1


def _is_stale(place: object, now: datetime) -> bool:
    value = getattr(place, "last_verified_at", None)
    if not isinstance(value, datetime):
        return False
    return value < now - timedelta(days=_stale_after_days(place))


def _stale_after_days(place: object) -> int:
    category = str(getattr(place, "category", "") or "").casefold()
    if category in STATIC_CATEGORIES:
        return STATIC_STALE_AFTER_DAYS
    return DYNAMIC_STALE_AFTER_DAYS if category in DYNAMIC_CATEGORIES else DYNAMIC_STALE_AFTER_DAYS


def _is_dynamic(place: object) -> bool:
    return str(getattr(place, "category", "") or "").casefold() in DYNAMIC_CATEGORIES
