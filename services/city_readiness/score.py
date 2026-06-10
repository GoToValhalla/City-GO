"""Route Readiness Score по городу."""

from __future__ import annotations

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.route_eligibility import route_eligible_sql_conditions

READY_MIN_SCORE = 70
READY_MIN_ELIGIBLE = 30
REVIEW_MIN_SCORE = 40


def compute_city_readiness(db: Session, *, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    base = db.query(Place).filter(Place.city_id == city.id)
    total = base.count()
    if total == 0:
        return _empty(city)
    metrics = _metrics(base, total)
    score = _weighted_score(metrics)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": score,
        "status": _status(score, int(metrics["eligible_places"]), metrics["coverage_pct"]),
        "components": metrics,
    }


def _metrics(base, total: int) -> dict[str, float]:
    with_coords = base.filter(Place.lat.isnot(None), Place.lng.isnot(None)).count()
    with_photo = base.filter(Place.image_url.isnot(None)).count()
    with_addr = base.filter(Place.address.isnot(None), Place.address != "").count()
    with_desc = base.filter(Place.short_description.isnot(None), Place.short_description != "").count()
    verified = base.filter(Place.verification_status == "verified").count()
    eligible = base.filter(*route_eligible_sql_conditions()).count()
    return {
        "places_total": total,
        "coverage_pct": round(with_coords / total * 100, 1),
        "photo_coverage_pct": round(with_photo / total * 100, 1),
        "address_coverage_pct": round(with_addr / total * 100, 1),
        "description_coverage_pct": round(with_desc / total * 100, 1),
        "route_eligibility_pct": round(eligible / total * 100, 1),
        "verification_coverage_pct": round(verified / total * 100, 1),
        "eligible_places": eligible,
    }


def _weighted_score(metrics: dict[str, float]) -> int:
    raw = (
        metrics["coverage_pct"] * 0.20
        + metrics["photo_coverage_pct"] * 0.20
        + metrics["address_coverage_pct"] * 0.15
        + metrics["description_coverage_pct"] * 0.10
        + metrics["route_eligibility_pct"] * 0.25
        + metrics["verification_coverage_pct"] * 0.10
    )
    return int(round(raw))


def _status(score: int, eligible_places: int, coverage_pct: float) -> str:
    if score >= READY_MIN_SCORE and eligible_places >= READY_MIN_ELIGIBLE and coverage_pct >= 90:
        return "ready"
    if score >= REVIEW_MIN_SCORE:
        return "needs_review"
    return "not_ready"


def _empty(city: City) -> dict[str, object]:
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": 0,
        "status": "not_ready",
        "components": {
            "places_total": 0,
            "coverage_pct": 0.0,
            "photo_coverage_pct": 0.0,
            "address_coverage_pct": 0.0,
            "description_coverage_pct": 0.0,
            "route_eligibility_pct": 0.0,
            "verification_coverage_pct": 0.0,
            "eligible_places": 0,
        },
    }
