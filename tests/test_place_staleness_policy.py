from datetime import datetime, timedelta
from types import SimpleNamespace

from services.place_staleness_policy import (
    PLACE_STATUS_ACTIVE,
    PLACE_STATUS_CLOSED,
    PLACE_STATUS_NEEDS_VERIFICATION,
    PLACE_STATUS_TEMPORARILY_CLOSED,
    effective_place_status,
    is_route_usable_place,
    normalize_place_status,
    staleness_penalty,
)


def test_normalize_place_status_defaults_to_active() -> None:
    assert normalize_place_status("unknown") == PLACE_STATUS_ACTIVE


def test_effective_place_status_marks_old_verification_as_stale() -> None:
    now = datetime(2026, 5, 28)
    place = SimpleNamespace(
        category="cafe",
        status=PLACE_STATUS_ACTIVE,
        last_verified_at=now - timedelta(days=31),
    )
    assert effective_place_status(place, now) == PLACE_STATUS_NEEDS_VERIFICATION


def test_static_place_uses_longer_staleness_window() -> None:
    now = datetime(2026, 5, 28)
    place = SimpleNamespace(
        category="museum",
        status=PLACE_STATUS_ACTIVE,
        last_verified_at=now - timedelta(days=31),
    )
    assert effective_place_status(place, now) == PLACE_STATUS_ACTIVE


def test_closed_place_is_not_route_usable() -> None:
    place = SimpleNamespace(status=PLACE_STATUS_CLOSED, is_active=True)
    assert is_route_usable_place(place) is False


def test_temporarily_closed_place_is_not_route_usable() -> None:
    place = SimpleNamespace(status=PLACE_STATUS_TEMPORARILY_CLOSED, is_active=True)
    assert is_route_usable_place(place) is False


def test_dynamic_stale_place_gets_strong_penalty_after_sixty_days() -> None:
    now = datetime(2026, 5, 28)
    place = SimpleNamespace(
        category="restaurant",
        status=PLACE_STATUS_ACTIVE,
        last_verified_at=now - timedelta(days=61),
    )
    assert staleness_penalty(place, now) == 0.2
