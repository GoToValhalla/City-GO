from __future__ import annotations

from dataclasses import dataclass

import pytest

from services.user_rating_foundation import aggregate_place_rating_from_reviews, public_rating_payload, validate_review_rating


@dataclass(frozen=True)
class ReviewStub:
    rating: int | None
    status: str


def test_aggregate_empty_reviews_produces_no_public_rating_new() -> None:
    result = aggregate_place_rating_from_reviews([])

    assert result.approved_count == 0
    assert result.rating_avg is None
    assert result.rating_histogram is None
    assert result.is_public is False
    assert public_rating_payload(result, public_reviews_enabled=True) is None


def test_aggregate_approved_reviews_only_new() -> None:
    result = aggregate_place_rating_from_reviews(
        [
            ReviewStub(rating=5, status="approved"),
            ReviewStub(rating=4, status="approved"),
            ReviewStub(rating=1, status="pending"),
            ReviewStub(rating=1, status="rejected"),
            ReviewStub(rating=1, status="hidden"),
            ReviewStub(rating=1, status="spam"),
        ]
    )

    assert result.approved_count == 2
    assert str(result.rating_avg) == "4.50"
    assert result.rating_histogram == {"1": 0, "2": 0, "3": 0, "4": 1, "5": 1}


def test_pending_rejected_hidden_spam_never_become_public_rating_new() -> None:
    result = aggregate_place_rating_from_reviews(
        [
            ReviewStub(rating=5, status="pending"),
            ReviewStub(rating=5, status="rejected"),
            ReviewStub(rating=5, status="hidden"),
            ReviewStub(rating=5, status="spam"),
        ]
    )

    assert result.approved_count == 0
    assert result.rating_avg is None
    assert public_rating_payload(result, public_reviews_enabled=True) is None


def test_public_rating_requires_public_reviews_flag_new() -> None:
    result = aggregate_place_rating_from_reviews([ReviewStub(rating=5, status="approved")])

    assert public_rating_payload(result, public_reviews_enabled=False) is None
    assert public_rating_payload(result, public_reviews_enabled=True) == {
        "approved_count": 1,
        "rating_avg": "5.00",
        "rating_histogram": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 1},
    }


def test_invalid_review_rating_rejected_at_schema_level_new() -> None:
    with pytest.raises(ValueError):
        validate_review_rating(0)
    with pytest.raises(ValueError):
        validate_review_rating(6)
