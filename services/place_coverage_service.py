from functools import reduce

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from schemas.place_coverage import PlaceCoverageReport
from services.place_coverage_counts import (
    average_confidence,
    count,
    has_coordinates,
    has_opening_hours,
    has_photo,
    has_real_address,
    has_source,
    has_visit_duration,
    is_route_eligible,
    is_verified,
    publication_status_counts,
    status_counts,
)
from services.place_coverage_route_score import (
    missing_route_categories,
    route_features,
    route_ready_score,
)
from services.place_staleness_policy import (
    PLACE_STATUS_ACTIVE,
    PLACE_STATUS_CLOSED,
    PLACE_STATUS_NEEDS_VERIFICATION,
    PLACE_STATUS_TEMPORARILY_CLOSED,
)


def build_place_coverage_report(db: Session, city_slug: str) -> PlaceCoverageReport:
    places = _city_places(db, city_slug)
    cat_counts = reduce(_count_category, places, {})
    total = len(places)
    opening = count(places, has_opening_hours)
    duration = count(places, has_visit_duration)
    statuses = status_counts(places)
    with_addr = count(places, has_real_address)
    with_ph = count(places, has_photo)
    return PlaceCoverageReport(
        city_slug=city_slug,
        total_places=total,
        with_coordinates=count(places, has_coordinates),
        with_opening_hours=opening,
        with_visit_duration=duration,
        with_source=count(places, has_source),
        active_places=statuses[PLACE_STATUS_ACTIVE],
        needs_verification=statuses[PLACE_STATUS_NEEDS_VERIFICATION],
        temporarily_closed_places=statuses[PLACE_STATUS_TEMPORARILY_CLOSED],
        closed_places=statuses[PLACE_STATUS_CLOSED],
        average_confidence=average_confidence(places),
        with_address=with_addr,
        without_address=total - with_addr,
        with_photo=with_ph,
        without_photo=total - with_ph,
        verified=count(places, is_verified),
        route_eligible=count(places, is_route_eligible),
        publication_status_breakdown=publication_status_counts(places),
        category_counts=cat_counts,
        route_features=route_features(places),
        missing_required_categories=missing_route_categories(cat_counts),
        route_ready_score=route_ready_score(total, opening, duration, cat_counts),
    )


def _city_places(db: Session, city_slug: str) -> list[Place]:
    return db.query(Place).join(City).filter(City.slug == city_slug).all()


def _count_category(counts: dict[str, int], place: Place) -> dict[str, int]:
    category = place.category or "unknown"
    return {**counts, category: counts.get(category, 0) + 1}
