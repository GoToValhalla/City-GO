"""Pure rating aggregation helpers for future public reviews.

Only approved review ratings are allowed to contribute to a public place rating.
No data-quality, confidence, readiness or route score can be substituted for stars.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

APPROVED_REVIEW_STATUS = "approved"
NON_PUBLIC_REVIEW_STATUSES = frozenset({"pending", "rejected", "hidden", "spam", "duplicate", "needs_more_info"})


class ReviewLike(Protocol):
    rating: int | None
    status: str


@dataclass(frozen=True)
class PlaceRatingResult:
    approved_count: int
    rating_avg: Decimal | None
    rating_histogram: dict[str, int] | None

    @property
    def is_public(self) -> bool:
        return self.approved_count > 0 and self.rating_avg is not None


def validate_review_rating(rating: int | None) -> None:
    if rating is None:
        return
    if rating < 1 or rating > 5:
        raise ValueError("review rating must be between 1 and 5")


def aggregate_place_rating_from_reviews(reviews: list[ReviewLike]) -> PlaceRatingResult:
    approved_ratings: list[int] = []
    histogram = {str(stars): 0 for stars in range(1, 6)}

    for review in reviews:
        validate_review_rating(review.rating)
        if review.status != APPROVED_REVIEW_STATUS or review.rating is None:
            continue
        approved_ratings.append(review.rating)
        histogram[str(review.rating)] += 1

    if not approved_ratings:
        return PlaceRatingResult(approved_count=0, rating_avg=None, rating_histogram=None)

    avg = (Decimal(sum(approved_ratings)) / Decimal(len(approved_ratings))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return PlaceRatingResult(approved_count=len(approved_ratings), rating_avg=avg, rating_histogram=histogram)


def public_rating_payload(result: PlaceRatingResult, *, public_reviews_enabled: bool) -> dict[str, object] | None:
    if not public_reviews_enabled or not result.is_public:
        return None
    return {
        "approved_count": result.approved_count,
        "rating_avg": str(result.rating_avg),
        "rating_histogram": result.rating_histogram,
    }
