from typing import cast

from sqlalchemy.orm import Session

from schemas.place_verification import PlaceVerificationEnqueueSummary
from services.place_verification_scheduler_service import (
    interval_hours_to_seconds,
    parse_city_slugs,
    run_scheduled_verification,
)


class FakeSession:
    def __init__(self) -> None:
        self.closed = False
        self.rolled_back = False

    def close(self) -> None:
        self.closed = True

    def rollback(self) -> None:
        self.rolled_back = True


def test_parse_city_slugs_trims_values_and_skips_empty_items() -> None:
    assert parse_city_slugs(" zelenogradsk, ,svetlogorsk ", "default") == (
        "zelenogradsk",
        "svetlogorsk",
    )


def test_parse_city_slugs_falls_back_to_default_city() -> None:
    assert parse_city_slugs("", "zelenogradsk") == ("zelenogradsk",)


def test_interval_hours_to_seconds_uses_safe_minimum() -> None:
    assert interval_hours_to_seconds(0) == 3600


def test_run_scheduled_verification_collects_success_and_errors() -> None:
    sessions: list[FakeSession] = []

    def session_factory() -> Session:
        session = FakeSession()
        sessions.append(session)
        return cast(Session, session)

    def enqueue(_db: Session, city_slug: str) -> PlaceVerificationEnqueueSummary:
        if city_slug == "broken":
            raise RuntimeError("db offline")
        return PlaceVerificationEnqueueSummary(city_slug=city_slug, enqueued=2, already_pending=1)

    results = run_scheduled_verification(session_factory, ("ok", "broken"), enqueue)

    assert [result.city_slug for result in results] == ["ok", "broken"]
    assert results[0].enqueued == 2
    assert results[1].error == "db offline"
    assert [session.closed for session in sessions] == [True, True]
    assert [session.rolled_back for session in sessions] == [False, True]
