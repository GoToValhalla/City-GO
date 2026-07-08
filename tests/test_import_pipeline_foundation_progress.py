"""Heartbeat progress and query-batching for long per-place foundation steps."""

from __future__ import annotations

from sqlalchemy import event

from models.city_admin_import_job import CityAdminImportJob
from services.import_pipeline_foundation_steps import (
    HEARTBEAT_EVERY_N_PLACES,
    _calculate_field_confidence,
    _field_row,
    _generate_ai_descriptions,
    _prefetch_field_confidence_cache,
)


def _job(db, city_id: int) -> CityAdminImportJob:
    job = CityAdminImportJob(city_id=city_id, status="running", source="admin_city_import")
    db.add(job)
    db.commit()
    return job


def _count_confidence_selects(db_session, action) -> int:
    counter = {"n": 0}

    def _before_execute(conn, clauseelement, multiparams, params, execution_options):
        sql = str(clauseelement).lower()
        if "place_field_confidence" in sql and "select" in sql:
            counter["n"] += 1

    event.listen(db_session.get_bind(), "before_execute", _before_execute)
    try:
        action()
    finally:
        event.remove(db_session.get_bind(), "before_execute", _before_execute)
    return counter["n"]


def test_calculate_field_confidence_updates_heartbeat_during_long_loop_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="progress-heartbeat-city")
    places = [place_factory(city_id=city.id, slug=f"heartbeat-place-{i}", title=f"Place {i}", category="park") for i in range(HEARTBEAT_EVERY_N_PLACES + 1)]
    job = _job(db_session, city.id)
    before = job.updated_at
    before_processed = job.processed_items

    _calculate_field_confidence(db_session, places, job)

    assert job.updated_at != before
    assert job.processed_items != before_processed
    assert job.processed_items == HEARTBEAT_EVERY_N_PLACES


def test_generate_ai_descriptions_updates_heartbeat_during_long_loop_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="progress-heartbeat-desc-city")
    places = [place_factory(city_id=city.id, slug=f"heartbeat-desc-place-{i}", title=f"Place {i}", category="park") for i in range(HEARTBEAT_EVERY_N_PLACES + 1)]
    job = _job(db_session, city.id)
    before = job.updated_at

    _generate_ai_descriptions(db_session, places, job)

    assert job.updated_at != before
    assert job.processed_items == HEARTBEAT_EVERY_N_PLACES


def test_no_heartbeat_below_threshold_new(db_session, city_factory, place_factory) -> None:
    """Behavior-preserving: fewer places than the heartbeat interval means no
    intermediate commit, same as before this change (only the final state matters)."""
    city = city_factory(slug="progress-no-heartbeat-city")
    places = [place_factory(city_id=city.id, slug=f"few-place-{i}", title=f"Place {i}", category="park") for i in range(3)]
    job = _job(db_session, city.id)
    before_processed = job.processed_items

    _calculate_field_confidence(db_session, places, job)

    assert job.processed_items == before_processed


def test_prefetch_field_confidence_cache_batches_queries_new(db_session, city_factory, place_factory) -> None:
    """Regression: _field_row's share of PlaceFieldConfidence lookups (previously
    one query per (place, field) pair - up to 9 fields x N places) must collapse
    to a single prefetch query for the whole batch plus zero further queries."""
    city = city_factory(slug="progress-batch-city")
    places = [place_factory(city_id=city.id, slug=f"batch-place-{i}", title=f"Place {i}", category="park") for i in range(10)]

    place_ids = [place.id for place in places]
    prefetch_query_count = _count_confidence_selects(db_session, lambda: _prefetch_field_confidence_cache(db_session, place_ids))
    assert prefetch_query_count == 1

    cache = _prefetch_field_confidence_cache(db_session, place_ids)
    fields = ("title", "coordinates", "address", "website", "phone", "category", "opening_hours", "description", "photo")

    def _lookup_all():
        for place in places:
            for field in fields:
                _field_row(db_session, place.id, field, cache=cache)

    # Before this change this loop (9 fields x 10 places = 90 lookups) issued one
    # SELECT each. With the cache, all 90 lookups are served from the single
    # prefetch above and issue zero further SELECTs.
    lookup_query_count = _count_confidence_selects(db_session, _lookup_all)
    assert lookup_query_count == 0
