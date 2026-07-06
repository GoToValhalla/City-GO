from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from models.destination import Destination, DestinationPlaceMembership
from models.destination_data_pipeline import DestinationDataPipelineRun
from models.place import Place
from models.place_merge_review import ReviewItem
from schemas.destination_data_pipeline import DestinationReadinessRead
from services.destination_bootstrap_service import destination_bootstrap_status


def build_destination_readiness(db: Session, destination: Destination) -> DestinationReadinessRead:
    query = _place_query(db, destination.id)
    total = query.count()
    published = _count(query.filter(Place.is_published.is_(True), Place.is_visible_in_catalog.is_(True)))
    route = _count(query.filter(Place.is_route_eligible.is_(True)))
    service_only = _count(query.filter(Place.internal_status == "service_only"))
    pending = _pending_reviews(db, destination.id)
    coverage = _coverage(query, total)
    score = _score(total, published, route, coverage, pending)
    last = _last_run(db, destination.id)
    bootstrap_ready, bootstrap_blockers = destination_bootstrap_status(db, destination)
    destination.readiness_score = score
    return DestinationReadinessRead(
        destination_slug=destination.slug,
        bootstrap_ready=bootstrap_ready,
        bootstrap_blockers=bootstrap_blockers,
        readiness_score=score,
        places_total=total,
        published_places=published,
        route_eligible_places=route,
        service_only_hidden=service_only,
        orphan_places=_orphan_count(db),
        memberships_total=db.query(DestinationPlaceMembership).filter_by(destination_id=destination.id).count(),
        pending_reviews=pending,
        completeness_score_avg=round(float(query.with_entities(func.avg(Place.completeness_score)).scalar() or 0), 2),
        degraded_sections=_degraded(coverage, pending),
        last_pipeline_run_status=last.status if last else None,
        last_pipeline_run_at=last.finished_at or last.started_at if last else None,
        **coverage,
    )


def _place_query(db: Session, destination_id: int) -> Query:
    return db.query(Place).join(DestinationPlaceMembership, DestinationPlaceMembership.place_id == Place.id).filter(DestinationPlaceMembership.destination_id == destination_id, DestinationPlaceMembership.is_hidden.is_(False), DestinationPlaceMembership.invalidated_at.is_(None))


def _coverage(query: Query, total: int) -> dict[str, float]:
    return {
        "address_coverage_pct": _pct(query.filter(Place.address.isnot(None)).count(), total),
        "photo_coverage_pct": _pct(query.filter(Place.image_url.isnot(None)).count(), total),
        "description_coverage_pct": _pct(query.filter(Place.short_description.isnot(None)).count(), total),
        "category_coverage_pct": _pct(query.filter(Place.canonical_category.isnot(None)).count(), total),
        "coordinates_coverage_pct": _pct(query.filter(Place.lat.isnot(None), Place.lng.isnot(None)).count(), total),
        "opening_hours_coverage_pct": _pct(query.filter(Place.opening_hours.isnot(None)).count(), total),
    }


def _score(total: int, published: int, route: int, coverage: dict[str, float], pending: int) -> int:
    if total <= 0:
        return 0
    base = (published / total) * 35 + (route / total) * 25 + sum(coverage.values()) / len(coverage) * 0.4
    return max(0, min(100, round(base - min(pending * 2, 20))))


def _degraded(coverage: dict[str, float], pending: int) -> list[str]:
    low = [key.replace("_coverage_pct", "") for key, value in coverage.items() if value < 50]
    return low + (["pending_reviews"] if pending else [])


def _pending_reviews(db: Session, destination_id: int) -> int:
    return _place_query(db, destination_id).join(ReviewItem, ReviewItem.place_id == Place.id).filter(ReviewItem.status == "pending").count()


def _orphan_count(db: Session) -> int:
    subq = db.query(DestinationPlaceMembership.place_id)
    return db.query(Place).filter(~Place.id.in_(subq)).count()


def _last_run(db: Session, destination_id: int) -> DestinationDataPipelineRun | None:
    return db.query(DestinationDataPipelineRun).filter_by(destination_id=destination_id).order_by(DestinationDataPipelineRun.created_at.desc()).first()


def _count(query: Query) -> int:
    return int(query.count())


def _pct(value: int, total: int) -> float:
    return round((value / total) * 100, 2) if total else 0.0
