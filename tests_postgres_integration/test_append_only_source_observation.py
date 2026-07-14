"""SourceObservation is the genuinely append-only import ledger in this
codebase (models/source_observation.py — unique on idempotency_key,
first_seen_at/last_seen_at, never row-deleted by import code).

CityAdminImportJob (the queue row) intentionally reuses one row per city
across re-queues (services/admin_city_import_job_service.py::_queue_job) —
that is the existing, tested, accepted design and is NOT append-only by
contract; this file does not attempt to change that.
"""
from __future__ import annotations

import threading

from sqlalchemy.exc import IntegrityError

from db.session import SessionLocal
from models.import_batch import ImportBatch
from models.source_observation import SourceObservation
from services.source_observation_service import create_source_observation

from conftest import unique_slug


def test_repeated_observation_updates_in_place_never_duplicates_new(pg_session, pg_city) -> None:
    batch = ImportBatch(city_id=pg_city.id, source_type="osm", mode="apply", dry_run=False)
    pg_session.add(batch)
    pg_session.commit()
    pg_session.refresh(batch)

    external_id = unique_slug("osm-node")
    first = create_source_observation(pg_session, batch.id, pg_city.id, external_id, {"name": "V1"})
    second = create_source_observation(pg_session, batch.id, pg_city.id, external_id, {"name": "V2"})

    assert first.id == second.id
    rows = pg_session.query(SourceObservation).filter(SourceObservation.idempotency_key == f"{batch.id}:{external_id}").all()
    assert len(rows) == 1
    assert rows[0].raw_payload["name"] == "V2"

    pg_session.query(SourceObservation).filter(SourceObservation.id == first.id).delete()
    pg_session.query(ImportBatch).filter(ImportBatch.id == batch.id).delete()
    pg_session.commit()


def test_concurrent_observation_writes_for_same_external_id_never_duplicate_rows_new(pg_session, pg_city) -> None:
    """Two concurrent import workers observing the same OSM object at the
    same time (idempotency_key collision) must converge on exactly one
    SourceObservation row via the IntegrityError/SAVEPOINT race handler in
    services/source_observation_service.py — this needs a real unique
    constraint violation across two live connections, unreachable on SQLite
    with the ORM's default isolation."""
    batch = ImportBatch(city_id=pg_city.id, source_type="osm", mode="apply", dry_run=False)
    pg_session.add(batch)
    pg_session.commit()
    pg_session.refresh(batch)
    batch_id = batch.id

    external_id = unique_slug("osm-node-race")
    errors: list[Exception] = []
    barrier = threading.Barrier(2)

    def writer(payload_name: str) -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=5)
            create_source_observation(session, batch_id, pg_city.id, external_id, {"name": payload_name})
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            session.close()

    threads = [threading.Thread(target=writer, args=(f"race-{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors, f"create_source_observation raised on a legitimate idempotency race: {errors}"

    rows = pg_session.query(SourceObservation).filter(SourceObservation.idempotency_key == f"{batch_id}:{external_id}").all()
    assert len(rows) == 1

    pg_session.query(SourceObservation).filter(SourceObservation.id == rows[0].id).delete()
    pg_session.query(ImportBatch).filter(ImportBatch.id == batch_id).delete()
    pg_session.commit()


def test_source_observation_idempotency_key_constraint_is_real_new(pg_session, pg_city) -> None:
    """The uq_source_observation_idempotency_key constraint must actually
    exist and be enforced by PostgreSQL, not just assumed at the ORM layer."""
    batch = ImportBatch(city_id=pg_city.id, source_type="osm", mode="apply", dry_run=False)
    pg_session.add(batch)
    pg_session.commit()
    pg_session.refresh(batch)

    key = unique_slug("dup-key")
    first = SourceObservation(
        import_batch_id=batch.id,
        city_id=pg_city.id,
        source_external_id="node-1",
        idempotency_key=key,
        raw_payload={},
        payload_hash="hash-1",
    )
    pg_session.add(first)
    pg_session.commit()

    duplicate = SourceObservation(
        import_batch_id=batch.id,
        city_id=pg_city.id,
        source_external_id="node-2",
        idempotency_key=key,
        raw_payload={},
        payload_hash="hash-2",
    )
    pg_session.add(duplicate)
    try:
        pg_session.commit()
        raise AssertionError("expected IntegrityError for duplicate idempotency_key")
    except IntegrityError:
        pg_session.rollback()

    pg_session.query(SourceObservation).filter(SourceObservation.id == first.id).delete()
    pg_session.query(ImportBatch).filter(ImportBatch.id == batch.id).delete()
    pg_session.commit()
