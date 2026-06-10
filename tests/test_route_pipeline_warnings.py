from datetime import datetime, timedelta
from types import SimpleNamespace

from services.route_pipeline_warnings import (
    ALL_FILTERED_WARNING,
    MALFORMED_OPENING_HOURS_WARNING,
    MISSING_OPENING_HOURS_WARNING,
    NO_CANDIDATES_WARNING,
    NO_ROUTE_POINTS_WARNING,
    STALE_PLACES_WARNING,
    assembly_warnings,
    candidate_warnings,
    filter_warnings,
)


def test_candidate_warnings_for_empty_pool() -> None:
    assert candidate_warnings([]) == [NO_CANDIDATES_WARNING]


def test_candidate_warnings_for_missing_and_malformed_hours() -> None:
    place = SimpleNamespace(
        opening_hours=None,
        validation={"issues": ["opening_hours_invalid_type"]},
    )
    assert candidate_warnings([place]) == [
        MISSING_OPENING_HOURS_WARNING,
        MALFORMED_OPENING_HOURS_WARNING,
    ]


def test_candidate_warnings_for_stale_places() -> None:
    place = SimpleNamespace(
        opening_hours={"mon": None},
        last_verified_at=datetime.utcnow() - timedelta(days=31),
        status="active",
    )
    assert candidate_warnings([place]) == [STALE_PLACES_WARNING]


def test_filter_warnings_when_all_candidates_removed() -> None:
    assert filter_warnings([object()], []) == [ALL_FILTERED_WARNING]


def test_assembly_warnings_when_route_is_empty() -> None:
    assert assembly_warnings([object()], []) == [NO_ROUTE_POINTS_WARNING]
