from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.city_import_scope import CityImportScope
from models.place_discovery_request import PlaceDiscoveryRequest
from models.place_source_presence import PlaceSourcePresence
from models.source_observation import SourceObservation
from schemas.city_expansion import ImportCoverageReport


def build_import_coverage_report(db: Session, city_slug: str, scope_code: str | None = None) -> ImportCoverageReport:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return ImportCoverageReport(city_slug=city_slug, scope_code=scope_code, blockers=["unknown_city"])
    scope = _scope_for_report(db, city, scope_code)
    return _report_for_city(db, city, scope, scope_code)


def _scope_for_report(db: Session, city: City, scope_code: str | None) -> CityImportScope | None:
    return _scope(db, city.id, scope_code)


def _report_for_city(
    db: Session,
    city: City,
    scope: CityImportScope | None,
    scope_code: str | None,
) -> ImportCoverageReport:
    observations = _observations(db, city.id, scope.id if scope else None)
    return ImportCoverageReport(
        city_slug=city.slug,
        scope_code=scope_code,
        import_state=_import_state(observations),
        raw_seen_count=observations,
        normalized_count=_count_status(db, city.id, scope, "normalized"),
        linked_to_places_count=_count_status(db, city.id, scope, "linked_to_place"),
        published_count=_count_match(db, city.id, scope, "matched_existing_place"),
        needs_review_count=_count_match(db, city.id, scope, "needs_review"),
        rejected_count=_rejected(db, city.id, scope),
        user_missing_reports_count=_discovery(db, city.id, scope),
        possible_removed_count=_possible_removed(db),
        coverage_status=_coverage_status(observations, scope),
        blockers=_blockers(observations, scope),
    )


def _import_state(observations: int) -> str:
    return "imported_raw" if observations else "not_started"


def _blockers(observations: int, scope: CityImportScope | None) -> list[str]:
    if observations:
        return []
    return ["scope_not_imported"] if scope else ["city_not_imported"]


def _scope(db: Session, city_id: int, code: str | None) -> CityImportScope | None:
    return db.query(CityImportScope).filter_by(city_id=city_id, code=code).first() if code else None


def _observations(db: Session, city_id: int, scope_id: int | None) -> int:
    return _base(db, city_id, scope_id).count()


def _base(db: Session, city_id: int, scope_id: int | None):
    query = db.query(SourceObservation).filter(SourceObservation.city_id == city_id)
    return query.filter(SourceObservation.scope_id == scope_id) if scope_id is not None else query


def _count_status(db: Session, city_id: int, scope: CityImportScope | None, status: str) -> int:
    return _base(db, city_id, scope.id if scope else None).filter(SourceObservation.normalization_status == status).count()


def _count_match(db: Session, city_id: int, scope: CityImportScope | None, status: str) -> int:
    return _base(db, city_id, scope.id if scope else None).filter(SourceObservation.match_status == status).count()


def _rejected(db: Session, city_id: int, scope: CityImportScope | None) -> int:
    return _base(db, city_id, scope.id if scope else None).filter(SourceObservation.rejection_reason.isnot(None)).count()


def _discovery(db: Session, city_id: int, scope: CityImportScope | None) -> int:
    query = db.query(PlaceDiscoveryRequest).filter(PlaceDiscoveryRequest.city_id == city_id)
    return query.filter(PlaceDiscoveryRequest.scope_id == scope.id).count() if scope else query.count()


def _possible_removed(db: Session) -> int:
    return db.query(func.count(PlaceSourcePresence.id)).filter(
        PlaceSourcePresence.presence_status == "possible_removed"
    ).scalar() or 0


def _coverage_status(raw_count: int, scope: CityImportScope | None) -> str:
    if raw_count == 0:
        return "not_started"
    return "published" if scope and scope.status == "published" else "review_needed"
