from models.feature_toggle import FeatureToggle
from models.search_routing_stage5 import SearchPlaceDocument
from services.data_foundation_projection_service import build_snapshot_from_place
from services.feature_toggle_service import update_toggle
from services.search_projection_rebuild_service import rebuild_search_place_documents


def _ready(db, place):
    db.add(build_snapshot_from_place(place, snapshot_version=1)); db.commit()
    rebuild_search_place_documents(db); db.commit()
    update_toggle(db, key="catalog_projection_reads_enabled", scope="global", scope_id=None, value_bool=True, actor="test")


def test_catalog_toggle_off_preserves_legacy(client, place_factory):
    place_factory(slug="legacy-catalog", title="Legacy Catalog")
    response = client.get("/places/")
    assert response.status_code == 200
    assert response.json()["items"][0]["slug"] == "legacy-catalog"


def test_catalog_toggle_on_lists_and_details_from_document(client, db_session, place_factory):
    place = place_factory(slug="projected-catalog", title="Projected Catalog")
    _ready(db_session, place)
    place.title = "Write Side Changed"; db_session.commit()
    listing = client.get("/places/", params={"city_slug": "zelenogradsk"})
    detail = client.get(f"/places/{place.id}")
    assert listing.status_code == detail.status_code == 200
    assert listing.json()["items"][0]["title"] == "Projected Catalog"
    assert detail.json()["title"] == "Projected Catalog"


def test_catalog_on_fails_closed_after_projection_row_removed(client, db_session, place_factory):
    place = place_factory(slug="missing-document")
    _ready(db_session, place)
    db_session.query(SearchPlaceDocument).delete(); db_session.commit()
    response = client.get("/places/", params={"city_id": place.city_id})
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "projection_incomplete"


def test_preexisting_unsafe_catalog_toggle_reports_missing(client, db_session):
    db_session.add(FeatureToggle(key="catalog_projection_reads_enabled", scope="global", scope_id=None, value_bool=True))
    db_session.commit()
    response = client.get("/places/")
    assert response.status_code == 503
    assert response.json()["detail"]["reason"] == "projection_missing"
