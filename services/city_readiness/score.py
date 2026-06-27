"""Route Readiness Score по городу."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Query, Session

from models.city import City
from models.data_foundation import CityQualitySnapshot
from models.place import Place
from models.route import Route
from services.data_quality.readiness import diagnostic_gates
from services.quality_scoring import apply_place_quality_scores
from services.route_eligibility import route_eligible_sql_conditions

READY_MIN_SCORE = 70
READY_MIN_ELIGIBLE = 30
REVIEW_MIN_SCORE = 40
STALE_AFTER_DAYS = 365


def compute_city_readiness(db: Session, *, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    return compute_city_readiness_for_city(db, city=city)


def compute_city_readiness_for_city(db: Session, *, city: City) -> dict[str, object]:
    base = db.query(Place).filter(Place.city_id == city.id)
    total = base.count()
    if total == 0:
        return _empty(db, city)
    metrics = _metrics(base, total, city.id)
    score = _weighted_score(metrics)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": score,
        "status": _status(score, int(metrics["eligible_places"]), metrics["coverage_pct"]),
        "components": metrics,
        "data_quality_diagnostics": diagnostic_gates(db, city_id=city.id, city_slug=city.slug),
    }


def recalculate_city_readiness_snapshot(
    db: Session,
    *,
    city_slug: str,
    reason: str = "city_readiness_recalculation",
    recalculate_place_scores: bool = True,
) -> dict[str, object] | None:
    """Recalculate place quality scores and persist a city readiness snapshot."""
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    if recalculate_place_scores:
        places = db.query(Place).filter(Place.city_id == city.id).all()
        apply_place_quality_scores(db, places, reason=reason)
    payload = compute_city_readiness_for_city(db, city=city)
    snapshot = _build_snapshot(city=city, payload=payload)
    db.add(snapshot)
    city.readiness_score = snapshot.readiness_score
    city.quality_status = snapshot.quality_status
    db.commit()
    db.refresh(snapshot)
    db.refresh(city)
    return {
        **payload,
        "snapshot_id": snapshot.id,
        "recalculated_places": int(payload["components"].get("places_total", 0)),
    }


def recalculate_all_city_readiness_snapshots(
    db: Session,
    *,
    reason: str = "city_readiness_recalculation",
    recalculate_place_scores: bool = True,
    limit: int | None = None,
) -> list[dict[str, object]]:
    query = db.query(City).order_by(City.name.asc())
    if limit is not None:
        query = query.limit(limit)
    rows: list[dict[str, object]] = []
    for city in query.all():
        payload = recalculate_city_readiness_snapshot(
            db,
            city_slug=city.slug,
            reason=reason,
            recalculate_place_scores=recalculate_place_scores,
        )
        if payload is not None:
            rows.append(payload)
    return rows


def latest_city_readiness_snapshot(db: Session, *, city_slug: str) -> CityQualitySnapshot | None:
    return (
        db.query(CityQualitySnapshot)
        .join(City, City.id == CityQualitySnapshot.city_id)
        .filter(City.slug == city_slug)
        .order_by(CityQualitySnapshot.created_at.desc(), CityQualitySnapshot.id.desc())
        .first()
    )


def _metrics(base: Query, total: int, city_id: int) -> dict[str, float | int]:
    active = base.filter(Place.is_active.is_(True), Place.lifecycle_status == "active").count()
    with_coords = base.filter(Place.lat.isnot(None), Place.lng.isnot(None)).count()
    with_photo = base.filter(Place.image_url.isnot(None), Place.image_url != "").count()
    with_addr = base.filter(Place.address.isnot(None), Place.address != "").count()
    with_desc = base.filter(Place.short_description.isnot(None), Place.short_description != "").count()
    with_hours = base.filter(Place.opening_hours.isnot(None)).count()
    verified = base.filter(Place.verification_status == "verified").count()
    eligible = base.filter(*route_eligible_sql_conditions()).count()
    published_routes = _published_routes(base.session, city_id)
    spam = base.filter(Place.is_spam_poi.is_(True)).count()
    stale = base.filter(Place.critical_field_expired.is_(True)).count()
    never_verified = base.filter(Place.verified_at.is_(None), Place.last_verified_at.is_(None)).count()
    gold = base.filter(Place.quality_tier == "gold").count()
    silver = base.filter(Place.quality_tier == "silver").count()
    bronze = base.filter(Place.quality_tier == "bronze").count()
    draft = base.filter(Place.quality_tier == "draft").count()
    rejected = base.filter(Place.quality_tier == "rejected").count()
    return {
        "places_total": total,
        "places_active": active,
        "coverage_pct": _pct(with_coords, total),
        "photo_coverage_pct": _pct(with_photo, total),
        "any_photo_pct": _pct(with_photo, total),
        "address_coverage_pct": _pct(with_addr, total),
        "address_full_pct": _pct(with_addr, total),
        "address_any_pct": _pct(with_addr, total),
        "description_coverage_pct": _pct(with_desc, total),
        "description_any_pct": _pct(with_desc, total),
        "hours_any_pct": _pct(with_hours, total),
        "route_eligibility_pct": _pct(eligible, total),
        "verification_coverage_pct": _pct(verified, total),
        "eligible_places": eligible,
        "published_routes": published_routes,
        "has_published_routes": int(published_routes > 0),
        "spam_poi_count": spam,
        "spam_poi_pct": _pct(spam, total),
        "gold_pct": _pct(gold, total),
        "silver_pct": _pct(silver, total),
        "bronze_pct": _pct(bronze, total),
        "draft_pct": _pct(draft, total),
        "rejected_pct": _pct(rejected, total),
        "stale_places_pct": _pct(stale, total),
        "never_verified_pct": _pct(never_verified, total),
    }


def _weighted_score(metrics: dict[str, float | int]) -> int:
    raw = (
        float(metrics["coverage_pct"]) * 0.20
        + float(metrics["photo_coverage_pct"]) * 0.20
        + float(metrics["address_coverage_pct"]) * 0.15
        + float(metrics["description_coverage_pct"]) * 0.10
        + float(metrics["route_eligibility_pct"]) * 0.25
        + float(metrics["verification_coverage_pct"]) * 0.10
    )
    return int(round(raw))


def _status(score: int, eligible_places: int, coverage_pct: float) -> str:
    if score >= READY_MIN_SCORE and eligible_places >= READY_MIN_ELIGIBLE and coverage_pct >= 90:
        return "ready"
    if score >= REVIEW_MIN_SCORE:
        return "needs_review"
    return "not_ready"


def _build_snapshot(*, city: City, payload: dict[str, object]) -> CityQualitySnapshot:
    components = payload["components"]
    assert isinstance(components, dict)
    return CityQualitySnapshot(
        city_id=city.id,
        readiness_score=int(payload["readiness_score"]),
        quality_status=str(payload["status"]),
        total_places_imported=int(components.get("places_total", 0)),
        total_places_active=int(components.get("places_active", 0)),
        total_places_route_eligible=int(components.get("eligible_places", 0)),
        spam_poi_count=int(components.get("spam_poi_count", 0)),
        spam_poi_pct=float(components.get("spam_poi_pct", 0.0)),
        photo_coverage_pct=float(components.get("photo_coverage_pct", 0.0)),
        any_photo_pct=float(components.get("any_photo_pct", 0.0)),
        address_full_pct=float(components.get("address_full_pct", 0.0)),
        address_any_pct=float(components.get("address_any_pct", 0.0)),
        description_any_pct=float(components.get("description_any_pct", 0.0)),
        hours_any_pct=float(components.get("hours_any_pct", 0.0)),
        gold_pct=float(components.get("gold_pct", 0.0)),
        silver_pct=float(components.get("silver_pct", 0.0)),
        bronze_pct=float(components.get("bronze_pct", 0.0)),
        draft_pct=float(components.get("draft_pct", 0.0)),
        rejected_pct=float(components.get("rejected_pct", 0.0)),
        avg_data_age_days=None,
        stale_places_pct=float(components.get("stale_places_pct", 0.0)),
        never_verified_pct=float(components.get("never_verified_pct", 0.0)),
        snapshot_payload=payload,
        created_at=datetime.utcnow(),
    )


def _pct(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total * 100, 1)


def _published_routes(db: Session, city_id: int) -> int:
    return db.query(Route).filter(Route.city_id == city_id, Route.is_active.is_(True)).count()


def _empty(db: Session, city: City) -> dict[str, object]:
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "readiness_score": 0,
        "status": "not_ready",
        "components": {
            "places_total": 0,
            "places_active": 0,
            "coverage_pct": 0.0,
            "photo_coverage_pct": 0.0,
            "any_photo_pct": 0.0,
            "address_coverage_pct": 0.0,
            "address_full_pct": 0.0,
            "address_any_pct": 0.0,
            "description_coverage_pct": 0.0,
            "description_any_pct": 0.0,
            "hours_any_pct": 0.0,
            "route_eligibility_pct": 0.0,
            "verification_coverage_pct": 0.0,
            "eligible_places": 0,
            "published_routes": 0,
            "has_published_routes": 0,
            "spam_poi_count": 0,
            "spam_poi_pct": 0.0,
            "gold_pct": 0.0,
            "silver_pct": 0.0,
            "bronze_pct": 0.0,
            "draft_pct": 0.0,
            "rejected_pct": 0.0,
            "stale_places_pct": 0.0,
            "never_verified_pct": 0.0,
        },
        "data_quality_diagnostics": diagnostic_gates(db, city_id=city.id, city_slug=city.slug),
    }
