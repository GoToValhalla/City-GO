from __future__ import annotations

from models.destination import DestinationPlaceMembership
from models.place import Place
from tests.destination_pipeline_helpers import destination_with_scope


def test_scope_import_creates_places_and_memberships_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="import-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    assert db_session.query(Place).filter(Place.slug.like("import-dest-core-%")).count() == 3
    assert db_session.query(DestinationPlaceMembership).filter_by(destination_id=dest.id).count() == 3


def test_repeated_import_does_not_duplicate_places_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="repeat-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    second = client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"}).json()["run"]
    assert db_session.query(Place).filter(Place.slug.like("repeat-dest-core-%")).count() == 3
    assert second["counters"]["duplicates_skipped"] == 3


def test_out_of_scope_candidate_ignored_and_service_only_hidden_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="scope-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    assert db_session.query(Place).filter(Place.slug == "scope-dest-core-outside").first() is None
    service = db_session.query(Place).filter(Place.slug == "scope-dest-core-bus-stop").one()
    assert service.internal_status == "service_only"
    assert service.is_visible_in_catalog is False
