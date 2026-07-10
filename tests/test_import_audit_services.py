from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.source_observation import SourceObservation
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


def test_create_source_observation_same_batch_same_item_produces_one_row_new(db_session):
    city, scope = _city_scope(db_session)
    batch = create_batch(db_session, scope)

    first = create_source_observation(db_session, batch.id, city.id, "node/1", {"name": "A"}, scope.id)
    second = create_source_observation(db_session, batch.id, city.id, "node/1", {"name": "B"}, scope.id)

    assert first.id == second.id
    rows = db_session.query(SourceObservation).filter_by(import_batch_id=batch.id).all()
    assert len(rows) == 1
    assert second.raw_payload == {"name": "B"}


def test_create_source_observation_different_batches_produce_two_rows_new(db_session):
    city, scope = _city_scope(db_session)
    batch_one = create_batch(db_session, scope)
    batch_two = create_batch(db_session, scope)

    first = create_source_observation(db_session, batch_one.id, city.id, "node/1", {"name": "A"}, scope.id)
    second = create_source_observation(db_session, batch_two.id, city.id, "node/1", {"name": "A"}, scope.id)

    assert first.id != second.id
    rows = db_session.query(SourceObservation).filter_by(source_external_id="node/1").all()
    assert len(rows) == 2


def test_create_source_observation_sets_correct_idempotency_key_new(db_session):
    city, scope = _city_scope(db_session)
    batch = create_batch(db_session, scope)

    observation = create_source_observation(db_session, batch.id, city.id, "node/1", {"name": "A"}, scope.id)

    assert observation.idempotency_key == f"{batch.id}:node/1"


def test_create_source_observation_duplicate_conflict_does_not_crash_new(db_session, monkeypatch):
    """Simulates a concurrent writer winning the race for the same
    idempotency_key: the pre-insert lookup misses, a colliding row is
    already committed, and the IntegrityError path must recover."""
    city, scope = _city_scope(db_session)
    batch = create_batch(db_session, scope)
    key = f"{batch.id}:node/1"

    winner = SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        scope_id=scope.id,
        source_type="osm",
        source_external_id="node/1",
        idempotency_key=key,
        payload_hash="concurrent-writer-hash",
        match_status="new_source_object",
        normalization_status="raw_only",
    )
    db_session.add(winner)
    db_session.commit()

    import services.source_observation_service as source_observation_service

    real_query = db_session.query
    call_count = {"n": 0}

    def _query_that_misses_once(model, *args, **kwargs):
        call_count["n"] += 1
        query = real_query(model, *args, **kwargs)
        if model is source_observation_service.SourceObservation and call_count["n"] == 1:
            return query.filter(SourceObservation.id == -1)
        return query

    monkeypatch.setattr(db_session, "query", _query_that_misses_once)

    result = create_source_observation(db_session, batch.id, city.id, "node/1", {"name": "A"}, scope.id)

    assert result.id == winner.id
    rows = db_session.query(SourceObservation).filter_by(idempotency_key=key).all()
    assert len(rows) == 1
