from models.place_published_snapshot import PublishedPlaceSnapshot
from models.search_routing_stage5 import ProjectionRebuildJob
from services.published_snapshot_rebuild_service import rebuild_published_place_snapshots
from services.projection_snapshot_source import latest_published_snapshots


def test_snapshot_rebuild_is_versioned_complete_and_preserves_publication_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="snapshot-city", name="Snapshot City")
    public = place_factory(city_id=city.id, is_published=True, is_route_eligible=True)
    hidden = place_factory(city_id=city.id, is_published=False, is_route_eligible=False)
    before = [(row.id, row.is_published, row.is_route_eligible) for row in (public, hidden)]

    first = rebuild_published_place_snapshots(db_session, city_id=city.id, actor="test")
    db_session.commit()
    second = rebuild_published_place_snapshots(db_session, city_id=city.id, actor="test")
    db_session.commit()

    assert first["status"] == second["status"] == "succeeded"
    assert first["actual_count"] == second["actual_count"] == 2
    assert second["source_snapshot_version"] == first["source_snapshot_version"] + 1
    rows = db_session.query(PublishedPlaceSnapshot).order_by(PublishedPlaceSnapshot.id).all()
    assert [(row.is_public, row.snapshot_version) for row in rows] == [
        (True, first["source_snapshot_version"]), (False, first["source_snapshot_version"]),
        (True, second["source_snapshot_version"]), (False, second["source_snapshot_version"]),
    ]
    db_session.expire_all()
    after = [(row.id, row.is_published, row.is_route_eligible) for row in (public, hidden)]
    assert after == before
    jobs = db_session.query(ProjectionRebuildJob).filter_by(projection_type="published_place_snapshot").all()
    assert all(job.is_complete and job.expected_count == job.actual_count == 2 for job in jobs)


def test_latest_snapshot_cannot_republish_an_unpublished_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="snapshot-unpublish", name="Snapshot Unpublish")
    place = place_factory(city_id=city.id, is_published=True, is_route_eligible=True)
    rebuild_published_place_snapshots(db_session, city_id=city.id, actor="test")
    db_session.commit()

    place.is_published = False
    rebuild_published_place_snapshots(db_session, city_id=city.id, actor="test")
    db_session.commit()

    assert latest_published_snapshots(db_session, city_id=city.id) == []
