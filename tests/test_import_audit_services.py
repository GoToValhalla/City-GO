from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from services.import_job_service import create_batch
from services.import_coverage_service import build_import_coverage_report
from services.place_scope_link_service import link_place_to_scope
from services.source_observation_service import create_source_observation
from services.source_presence_service import mark_missing, mark_seen


def _city_scope(db_session):
    city = City(slug="zelenogradsk", name="Зеленоградск", country="Россия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="center", name="Центр", enabled=True, status="published")
    db_session.add(scope)
    db_session.commit()
    return city, scope


def test_source_observation_keeps_rejection_reason_and_coverage(db_session):
    city, scope = _city_scope(db_session)
    batch = create_batch(db_session, scope)
    observation = create_source_observation(
        db_session, batch.id, city.id, "node/1", {"name": None}, scope.id, "missing_name",
    )
    report = build_import_coverage_report(db_session, "zelenogradsk", "center")
    assert observation.rejection_reason == "missing_name"
    assert report.rejected_count == 1
    assert report.coverage_status == "published"


def test_source_presence_requires_repeated_missing_before_possible_removed(db_session):
    _city, scope = _city_scope(db_session)
    batch = create_batch(db_session, scope)
    row = mark_seen(db_session, "osm", "node/1", batch.id)
    assert mark_missing(db_session, row).presence_status == "missing_once"
    assert mark_missing(db_session, row).presence_status == "missing_repeatedly"
    assert mark_missing(db_session, row).presence_status == "possible_removed"


def test_place_scope_link_deduplicates_overlapping_scope_link(db_session):
    city, scope = _city_scope(db_session)
    place = Place(city_id=city.id, slug="p1", title="P1", lat=1, lng=2)
    db_session.add(place)
    db_session.commit()
    first = link_place_to_scope(db_session, place.id, scope.id)
    second = link_place_to_scope(db_session, place.id, scope.id)
    assert first.id == second.id
