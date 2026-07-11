"""Bounded chunk commits + safe resume for _apply_import.

Chunk size is 50 completed items; a SourceObservation with a non-NULL
processing_outcome is the durable "this item is fully done" marker. A crash
(simulated here as an exception raised partway through processing, followed
by a fresh _apply_import call against the SAME batch_id, in a fresh session
to model an independent process attempt) must be able to resume without
reprocessing completed items, without producing duplicate rows, and without
depending on item order.
"""

from __future__ import annotations

import os
import random
import tempfile
import uuid

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from data.scripts.import_city_osm import _apply_import, _normalize_osm_object
from db.base import Base
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from models.review_queue_item import ReviewQueueItem
from models.source_observation import SourceObservation
from services.import_job_service import create_batch


@pytest.fixture
def isolated_engine():
    """A private, function-scoped SQLite file engine — NOT the shared
    session-scoped `engine` fixture. Crash/resume tests here perform real,
    separate-session commits to model independent process attempts, and the
    shared `engine` fixture lives for the whole pytest session, so any real
    commit against it leaks rows (e.g. Category.code, unique) into every
    other test that reuses that same fixture for the rest of the run. This
    fixture gives each test its own on-disk DB, fully disposed and deleted
    on teardown, so real commits stay contained to one test."""
    db_path = os.path.join(tempfile.gettempdir(), f"citygo-chunk-resume-{uuid.uuid4().hex}.db")
    db_url = f"sqlite:///{db_path}"
    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})

    @event.listens_for(test_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(test_engine)
    try:
        yield test_engine
    finally:
        test_engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


def _new_session(engine):
    """A fresh session bound directly to the given engine, modeling an
    independent process attempt — unlike db_session, whose single connection/
    transaction makes an internal commit-then-rollback within one test lose
    previously committed rows (SQLAlchemy session-on-Connection semantics),
    which does not reflect how two real separate invocations behave."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _city_scope(session, *, slug="riga"):
    city = City(slug=slug, name="Рига", country="Латвия")
    session.add(city)
    session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    session.add(scope)
    session.commit()
    return city.id, scope.id


def _raw_items(count: int, *, id_offset: int = 0):
    return [
        {
            "type": "node",
            "id": id_offset + i,
            "lat": 54.6 + i * 0.001,
            "lon": 24.1 + i * 0.001,
            "tags": {"name": f"Place {id_offset + i}", "amenity": "cafe"},
        }
        for i in range(count)
    ]


def _normalized(raw_items, city_slug):
    return [_normalize_osm_object(item, city_slug) for item in raw_items]


def test_boundary_49_items_single_chunk_no_intermediate_commit_marker_new(db_session):
    city_id, scope_id = _city_scope(db_session)
    city = db_session.query(City).filter(City.id == city_id).one()
    scope = db_session.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    raw = _raw_items(49, id_offset=100000)
    result = _apply_import(db_session, city, scope, "tourist_core", raw, _normalized(raw, city.slug))

    assert result["created"] == 49
    completed = db_session.query(SourceObservation).filter(
        SourceObservation.processing_outcome.isnot(None)
    ).count()
    assert completed == 49


def test_boundary_50_items_exactly_one_chunk_new(db_session):
    city_id, scope_id = _city_scope(db_session)
    city = db_session.query(City).filter(City.id == city_id).one()
    scope = db_session.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    raw = _raw_items(50, id_offset=200000)
    result = _apply_import(db_session, city, scope, "tourist_core", raw, _normalized(raw, city.slug))

    assert result["created"] == 50
    completed = db_session.query(SourceObservation).filter(
        SourceObservation.processing_outcome.isnot(None)
    ).count()
    assert completed == 50


def test_boundary_51_items_two_chunks_new(db_session):
    city_id, scope_id = _city_scope(db_session)
    city = db_session.query(City).filter(City.id == city_id).one()
    scope = db_session.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    raw = _raw_items(51, id_offset=300000)
    result = _apply_import(db_session, city, scope, "tourist_core", raw, _normalized(raw, city.slug))

    assert result["created"] == 51
    completed = db_session.query(SourceObservation).filter(
        SourceObservation.processing_outcome.isnot(None)
    ).count()
    assert completed == 51


def test_crash_before_first_commit_then_resume_produces_same_result_new(isolated_engine, monkeypatch):
    """A crash immediately after the batch row exists (zero items processed)
    must allow a full, clean resume against the same batch_id."""
    setup = _new_session(isolated_engine)
    city_id, scope_id = _city_scope(setup, slug="riga-crash-before-first-commit")
    batch_id = create_batch(setup, setup.query(CityImportScope).filter(CityImportScope.id == scope_id).one(), mode="apply").id
    setup.close()

    raw = _raw_items(10, id_offset=400000)
    normalized = _normalized(raw, "riga-crash-before-first-commit")

    import data.scripts.import_city_osm as import_city_osm

    call_count = {"n": 0}
    real_process = import_city_osm._process_one_item

    def _crash_on_first_call(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated crash before any item completes")
        return real_process(*args, **kwargs)

    monkeypatch.setattr(import_city_osm, "_process_one_item", _crash_on_first_call)

    attempt_one = _new_session(isolated_engine)
    city = attempt_one.query(City).filter(City.id == city_id).one()
    scope = attempt_one.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    with pytest.raises(RuntimeError):
        _apply_import(attempt_one, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_one.close()

    monkeypatch.setattr(import_city_osm, "_process_one_item", real_process)

    attempt_two = _new_session(isolated_engine)
    city = attempt_two.query(City).filter(City.id == city_id).one()
    scope = attempt_two.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    result = _apply_import(attempt_two, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)

    assert result["created"] == 10
    places = attempt_two.query(Place).filter(Place.city_id == city_id).count()
    assert places == 10
    attempt_two.close()


def test_crash_after_first_chunk_then_resume_no_duplicates_new(isolated_engine, monkeypatch):
    """A crash after chunk 1 (50 items committed) but before chunk 2 finishes
    must resume only the remaining, not-yet-completed items."""
    setup = _new_session(isolated_engine)
    city_id, scope_id = _city_scope(setup, slug="riga-crash-after-first-chunk")
    batch_id = create_batch(setup, setup.query(CityImportScope).filter(CityImportScope.id == scope_id).one(), mode="apply").id
    setup.close()

    raw = _raw_items(75, id_offset=500000)
    normalized = _normalized(raw, "riga-crash-after-first-chunk")

    import data.scripts.import_city_osm as import_city_osm

    call_count = {"n": 0}
    real_process = import_city_osm._process_one_item

    def _crash_after_60(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 61:
            raise RuntimeError("simulated crash mid second chunk")
        return real_process(*args, **kwargs)

    monkeypatch.setattr(import_city_osm, "_process_one_item", _crash_after_60)

    attempt_one = _new_session(isolated_engine)
    city = attempt_one.query(City).filter(City.id == city_id).one()
    scope = attempt_one.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    with pytest.raises(RuntimeError):
        _apply_import(attempt_one, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_one.close()

    verify = _new_session(isolated_engine)
    completed_before_resume = verify.query(SourceObservation).filter(
        SourceObservation.import_batch_id == batch_id,
        SourceObservation.processing_outcome.isnot(None),
    ).count()
    assert completed_before_resume == 50
    verify.close()

    monkeypatch.setattr(import_city_osm, "_process_one_item", real_process)
    attempt_two = _new_session(isolated_engine)
    city = attempt_two.query(City).filter(City.id == city_id).one()
    scope = attempt_two.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    result = _apply_import(attempt_two, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)

    assert result["created"] == 75
    places = attempt_two.query(Place).filter(Place.city_id == city_id).count()
    assert places == 75
    observations = attempt_two.query(SourceObservation).filter(SourceObservation.import_batch_id == batch_id).count()
    assert observations == 75
    scope_links = attempt_two.query(PlaceScopeLink).filter(PlaceScopeLink.scope_id == scope_id).count()
    assert scope_links == 75
    presences = (
        attempt_two.query(PlaceSourcePresence)
        .join(Place, Place.id == PlaceSourcePresence.place_id)
        .filter(Place.city_id == city_id, PlaceSourcePresence.source_type == "osm")
        .count()
    )
    assert presences == 75
    attempt_two.close()


def test_incomplete_null_outcome_observation_is_reprocessed_new(db_session):
    """A SourceObservation created but never finished (processing_outcome
    still NULL, simulating an interrupted _save_source_observation call with
    no further writes) must be picked up and fully completed on retry, not
    treated as already-done."""
    city_id, scope_id = _city_scope(db_session)
    city = db_session.query(City).filter(City.id == city_id).one()
    scope = db_session.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    batch = create_batch(db_session, scope, mode="apply")
    raw = _raw_items(1, id_offset=600000)
    normalized = _normalized(raw, city.slug)

    incomplete = SourceObservation(
        import_batch_id=batch.id,
        city_id=city.id,
        scope_id=scope.id,
        source_type="osm",
        source_external_id=normalized[0]["source_external_id"],
        idempotency_key=f"{batch.id}:{normalized[0]['source_external_id']}",
        payload_hash=normalized[0]["payload_hash"],
        match_status="new_source_object",
        normalization_status="raw_only",
        processing_outcome=None,
    )
    db_session.add(incomplete)
    db_session.commit()

    result = _apply_import(db_session, city, scope, "tourist_core", raw, normalized, batch_id=batch.id)

    assert result["created"] == 1
    observation = db_session.query(SourceObservation).filter_by(id=incomplete.id).first()
    assert observation.processing_outcome == "created"
    assert observation.canonical_place_id is not None
    places = db_session.query(Place).filter(Place.city_id == city.id).count()
    assert places == 1


def test_same_input_different_order_produces_identical_result_new(db_session):
    city_a_id, scope_a_id = _city_scope(db_session, slug="riga-a")
    city_a = db_session.query(City).filter(City.id == city_a_id).one()
    scope_a = db_session.query(CityImportScope).filter(CityImportScope.id == scope_a_id).one()
    raw = _raw_items(60, id_offset=700000)
    normalized_first_order = _normalized(raw, city_a.slug)

    batch_a = create_batch(db_session, scope_a, mode="apply")
    result_a = _apply_import(db_session, city_a, scope_a, "tourist_core", raw, normalized_first_order, batch_id=batch_a.id)

    city_b_id, scope_b_id = _city_scope(db_session, slug="riga-b")
    city_b = db_session.query(City).filter(City.id == city_b_id).one()
    scope_b = db_session.query(CityImportScope).filter(CityImportScope.id == scope_b_id).one()

    shuffled_raw = list(raw)
    random.Random(42).shuffle(shuffled_raw)
    normalized_shuffled = _normalized(shuffled_raw, city_b.slug)

    batch_b = create_batch(db_session, scope_b, mode="apply")
    result_b = _apply_import(db_session, city_b, scope_b, "tourist_core", shuffled_raw, normalized_shuffled, batch_id=batch_b.id)

    assert result_a["created"] == result_b["created"] == 60
    assert result_a["updated"] == result_b["updated"]
    assert result_a["unchanged"] == result_b["unchanged"]
    assert result_a["needs_review"] == result_b["needs_review"]
    assert result_a["rejected"] == result_b["rejected"]


def test_resume_produces_no_duplicate_review_queue_items_new(isolated_engine, monkeypatch):
    """Items that end up in the review queue (needs_review/hidden paths)
    must not get a second ReviewQueueItem row when a crash+resume causes
    _save_source_observation's update path to run twice for the same item."""
    setup = _new_session(isolated_engine)
    city_id, scope_id = _city_scope(setup, slug="riga-review-dup")
    city = setup.query(City).filter(City.id == city_id).one()
    scope = setup.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    batch_one_id = create_batch(setup, scope, mode="apply").id

    raw_v1 = [{"type": "node", "id": 1000500, "lat": 54.6, "lon": 24.1, "tags": {"name": "Original Name", "amenity": "cafe"}}]
    _apply_import(setup, city, scope, "tourist_core", raw_v1, _normalized(raw_v1, city.slug), batch_id=batch_one_id)

    # A genuinely SECOND import run (its own batch) against the same
    # real-world OSM object, with a changed name — this is what triggers the
    # needs_review decision and review-queue write, not a resume of batch one.
    batch_two_id = create_batch(setup, scope, mode="apply").id
    setup.close()

    raw_v2 = [{"type": "node", "id": 1000500, "lat": 54.6, "lon": 24.1, "tags": {"name": "Changed Name", "amenity": "cafe"}}]
    normalized_v2 = _normalized(raw_v2, "riga-review-dup")

    import data.scripts.import_city_osm as import_city_osm

    call_count = {"n": 0}
    real_process = import_city_osm._process_one_item

    def _crash_first_time(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated crash")
        return real_process(*args, **kwargs)

    monkeypatch.setattr(import_city_osm, "_process_one_item", _crash_first_time)
    attempt_one = _new_session(isolated_engine)
    city = attempt_one.query(City).filter(City.id == city_id).one()
    scope = attempt_one.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    with pytest.raises(RuntimeError):
        _apply_import(attempt_one, city, scope, "tourist_core", raw_v2, normalized_v2, batch_id=batch_two_id)
    attempt_one.close()

    monkeypatch.setattr(import_city_osm, "_process_one_item", real_process)
    attempt_two = _new_session(isolated_engine)
    city = attempt_two.query(City).filter(City.id == city_id).one()
    scope = attempt_two.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    _apply_import(attempt_two, city, scope, "tourist_core", raw_v2, normalized_v2, batch_id=batch_two_id)

    place = attempt_two.query(Place).filter(Place.city_id == city_id).first()
    review_items = attempt_two.query(ReviewQueueItem).filter(ReviewQueueItem.place_id == place.id).count()
    assert review_items == 1
    attempt_two.close()


def test_exact_counters_after_resume_match_uninterrupted_run_new(isolated_engine, monkeypatch):
    baseline = _new_session(isolated_engine)
    baseline_city_id, baseline_scope_id = _city_scope(baseline, slug="riga-baseline")
    baseline_city = baseline.query(City).filter(City.id == baseline_city_id).one()
    baseline_scope = baseline.query(CityImportScope).filter(CityImportScope.id == baseline_scope_id).one()
    raw = _raw_items(60, id_offset=800000)
    baseline_normalized = _normalized(raw, baseline_city.slug)
    baseline_result = _apply_import(baseline, baseline_city, baseline_scope, "tourist_core", raw, baseline_normalized)
    baseline.close()

    setup = _new_session(isolated_engine)
    city_id, scope_id = _city_scope(setup, slug="riga-resume")
    batch_id = create_batch(setup, setup.query(CityImportScope).filter(CityImportScope.id == scope_id).one(), mode="apply").id
    setup.close()

    normalized = _normalized(raw, "riga-resume")

    import data.scripts.import_city_osm as import_city_osm

    call_count = {"n": 0}
    real_process = import_city_osm._process_one_item

    def _crash_at_55(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 55:
            raise RuntimeError("simulated crash")
        return real_process(*args, **kwargs)

    monkeypatch.setattr(import_city_osm, "_process_one_item", _crash_at_55)
    attempt_one = _new_session(isolated_engine)
    city = attempt_one.query(City).filter(City.id == city_id).one()
    scope = attempt_one.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    with pytest.raises(RuntimeError):
        _apply_import(attempt_one, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_one.close()

    monkeypatch.setattr(import_city_osm, "_process_one_item", real_process)
    attempt_two = _new_session(isolated_engine)
    city = attempt_two.query(City).filter(City.id == city_id).one()
    scope = attempt_two.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    result = _apply_import(attempt_two, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_two.close()

    assert result["created"] == baseline_result["created"] == 60
    assert result["updated"] == baseline_result["updated"]
    assert result["unchanged"] == baseline_result["unchanged"]
    assert result["needs_review"] == baseline_result["needs_review"]
    assert result["rejected"] == baseline_result["rejected"]
    assert result["hidden"] == baseline_result["hidden"]


def test_missing_source_and_bad_place_final_steps_run_once_after_resume_new(isolated_engine, monkeypatch):
    """_hide_bad_existing_places and _mark_missing_sources must run exactly
    once per _apply_import call, after all item chunks — including the
    resumed call, not duplicated across the crashed+resumed pair."""
    setup = _new_session(isolated_engine)
    city_id, scope_id = _city_scope(setup, slug="riga-missing-final-steps")
    city = setup.query(City).filter(City.id == city_id).one()
    scope = setup.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    old_place = Place(city_id=city.id, slug="old-missing", title="Old Missing", lat=54.6, lng=24.1)
    setup.add(old_place)
    setup.commit()
    setup.add(PlaceScopeLink(place_id=old_place.id, scope_id=scope.id, relation_type="imported_from_scope"))
    setup.add(
        PlaceSourcePresence(
            place_id=old_place.id,
            source_type="osm",
            source_profile="tourist_core",
            source_external_id="osm:node:old-missing",
        )
    )
    setup.commit()
    batch_id = create_batch(setup, scope, mode="apply").id
    setup.close()

    raw = _raw_items(5, id_offset=900000)
    normalized = _normalized(raw, "riga-missing-final-steps")

    import data.scripts.import_city_osm as import_city_osm

    call_count = {"n": 0}
    real_process = import_city_osm._process_one_item
    hide_bad_calls = {"n": 0}
    mark_missing_calls = {"n": 0}
    real_hide_bad = import_city_osm._hide_bad_existing_places
    real_mark_missing = import_city_osm._mark_missing_sources

    def _counting_hide_bad(*args, **kwargs):
        hide_bad_calls["n"] += 1
        return real_hide_bad(*args, **kwargs)

    def _counting_mark_missing(*args, **kwargs):
        mark_missing_calls["n"] += 1
        return real_mark_missing(*args, **kwargs)

    def _crash_on_third(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 3:
            raise RuntimeError("simulated crash")
        return real_process(*args, **kwargs)

    monkeypatch.setattr(import_city_osm, "_process_one_item", _crash_on_third)
    monkeypatch.setattr(import_city_osm, "_hide_bad_existing_places", _counting_hide_bad)
    monkeypatch.setattr(import_city_osm, "_mark_missing_sources", _counting_mark_missing)

    attempt_one = _new_session(isolated_engine)
    city = attempt_one.query(City).filter(City.id == city_id).one()
    scope = attempt_one.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    with pytest.raises(RuntimeError):
        _apply_import(attempt_one, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_one.close()

    assert hide_bad_calls["n"] == 0
    assert mark_missing_calls["n"] == 0

    monkeypatch.setattr(import_city_osm, "_process_one_item", real_process)
    attempt_two = _new_session(isolated_engine)
    city = attempt_two.query(City).filter(City.id == city_id).one()
    scope = attempt_two.query(CityImportScope).filter(CityImportScope.id == scope_id).one()
    result = _apply_import(attempt_two, city, scope, "tourist_core", raw, normalized, batch_id=batch_id)
    attempt_two.close()

    assert hide_bad_calls["n"] == 1
    assert mark_missing_calls["n"] == 1
    assert result["missing_from_source"] == 1
