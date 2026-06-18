"""Data Foundation quality scoring for places.

The scoring contract is intentionally deterministic and local to a Place row so it can run
inside imports, admin actions, scripts and tests without external services.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from sqlalchemy.orm import Session

from models.data_foundation import QualityScoreHistory
from models.place import Place
from services.route_eligibility import evaluate_place_route_eligibility

GOLD_MIN_SCORE = 80
SILVER_MIN_SCORE = 55
BRONZE_MIN_SCORE = 30


@dataclass(frozen=True)
class QualityScoreResult:
    quality_score: int
    quality_tier: str
    completeness_score: int
    photo_score: int
    description_score: int
    confidence_score: int
    freshness_score: int
    route_eligible: bool
    route_eligibility_reasons: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "quality_score": self.quality_score,
            "quality_tier": self.quality_tier,
            "completeness_score": self.completeness_score,
            "photo_score": self.photo_score,
            "description_score": self.description_score,
            "confidence_score": self.confidence_score,
            "freshness_score": self.freshness_score,
            "route_eligible": self.route_eligible,
            "route_eligibility_reasons": list(self.route_eligibility_reasons),
        }


def score_place_quality(place: Place, *, now: datetime | None = None) -> QualityScoreResult:
    """Return Data Foundation quality score components for one place."""
    now = now or datetime.utcnow()
    completeness_score = _completeness_score(place)
    photo_score = _photo_score(place)
    description_score = _description_score(place)
    confidence_score = _confidence_score(place)
    freshness_score = _freshness_score(place, now=now)
    quality_score = _clamp_score(
        completeness_score
        + photo_score
        + description_score
        + confidence_score
        + freshness_score,
        minimum=0,
        maximum=100,
    )
    quality_tier = _quality_tier(place, quality_score)
    eligibility = _evaluate_with_projected_quality_tier(place, quality_tier=quality_tier)
    return QualityScoreResult(
        quality_score=quality_score,
        quality_tier=quality_tier,
        completeness_score=completeness_score,
        photo_score=photo_score,
        description_score=description_score,
        confidence_score=confidence_score,
        freshness_score=freshness_score,
        route_eligible=eligibility.eligible,
        route_eligibility_reasons=eligibility.reasons,
    )


def apply_place_quality_score(
    db: Session,
    place: Place,
    *,
    reason: str = "quality_recalculation",
    now: datetime | None = None,
    write_history: bool = True,
) -> QualityScoreResult:
    """Recalculate and persist quality fields for one Place."""
    result = score_place_quality(place, now=now)
    place.quality_score = result.quality_score
    place.quality_tier = result.quality_tier
    place.completeness_score = result.completeness_score
    place.photo_score = result.photo_score
    place.description_score = result.description_score
    place.confidence_score = result.confidence_score
    place.freshness_score = result.freshness_score
    place.is_route_eligible = result.route_eligible
    place.route_exclusion_reason = None if result.route_eligible else ",".join(result.route_eligibility_reasons)

    if write_history:
        db.add(
            QualityScoreHistory(
                place_id=place.id,
                quality_score=result.quality_score,
                quality_tier=result.quality_tier,
                completeness_score=result.completeness_score,
                photo_score=result.photo_score,
                description_score=result.description_score,
                confidence_score=result.confidence_score,
                freshness_score=result.freshness_score,
                reason=reason,
            )
        )
    return result


def apply_place_quality_scores(
    db: Session,
    places: Iterable[Place],
    *,
    reason: str = "quality_recalculation",
    now: datetime | None = None,
    write_history: bool = True,
) -> int:
    """Recalculate quality fields for an iterable of places and return affected count."""
    affected = 0
    timestamp = now or datetime.utcnow()
    for place in places:
        apply_place_quality_score(db, place, reason=reason, now=timestamp, write_history=write_history)
        affected += 1
    return affected


def _completeness_score(place: Place) -> int:
    score = 0
    if _has_text(place.title):
        score += 5
    if _has_text(getattr(place, "canonical_category", None) or place.category):
        score += 6
    if place.lat is not None and place.lng is not None and not (place.lat == 0.0 and place.lng == 0.0):
        score += 7
    if _has_text(place.address):
        score += 8
    if place.opening_hours:
        score += 5
    if place.average_visit_duration_minutes:
        score += 4
    if place.price_level is not None:
        score += 3
    if place.indoor or place.outdoor or place.dog_friendly or place.family_friendly:
        score += 2
    return min(score, 40)


def _photo_score(place: Place) -> int:
    has_image_url = _has_text(place.image_url)
    image_count = len(getattr(place, "images", []) or [])
    if has_image_url and image_count >= 2:
        return 25
    if has_image_url or image_count >= 1:
        return 20
    return 0


def _description_score(place: Place) -> int:
    description = (place.short_description or "").strip()
    if len(description) >= 180:
        return 15
    if len(description) >= 80:
        return 12
    if len(description) >= 24:
        return 8
    return 0


def _confidence_score(place: Place) -> int:
    if place.existence_confidence_score is not None and place.existence_confidence_score > 0:
        return _clamp_score(round(place.existence_confidence_score / 10), minimum=0, maximum=10)
    if place.confidence is None:
        return 5
    confidence = place.confidence
    if confidence <= 1:
        confidence *= 10
    return _clamp_score(round(confidence), minimum=0, maximum=10)


def _freshness_score(place: Place, *, now: datetime) -> int:
    reference = place.verified_at or place.last_verified_at or place.address_updated_at or place.updated_at or place.created_at
    if reference is None:
        return 0
    age_days = max((now - reference).days, 0)
    if age_days <= 30:
        return 10
    if age_days <= 90:
        return 8
    if age_days <= 180:
        return 6
    if age_days <= 365:
        return 4
    return 2


def _quality_tier(place: Place, quality_score: int) -> str:
    if getattr(place, "is_spam_poi", False) or getattr(place, "lifecycle_status", "active") == "rejected":
        return "rejected"
    if quality_score >= GOLD_MIN_SCORE:
        return "gold"
    if quality_score >= SILVER_MIN_SCORE:
        return "silver"
    if quality_score >= BRONZE_MIN_SCORE:
        return "bronze"
    return "draft"


def _evaluate_with_projected_quality_tier(place: Place, *, quality_tier: str):
    original_quality_tier = place.quality_tier
    try:
        place.quality_tier = quality_tier
        return evaluate_place_route_eligibility(place)
    finally:
        place.quality_tier = original_quality_tier


def _has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def _clamp_score(value: int | float, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(round(value))))
