from __future__ import annotations

from services.place_query_params_service import normalize_place_query_params
from schemas.place_query_params import PlaceQueryParams
from tests.destination_pipeline_helpers import destination_with_scope


def test_public_catalog_destination_slug_filters_clean_places_new(client, db_session, city_factory, monkeypatch):
    monkeypatch.setattr("services.destination_flags.destination_catalog_reads_enabled", lambda: True)
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="catalog-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "full"})
    response = client.get("/places/", params={"destination_slug": dest.slug})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert "source" not in payload["items"][0]
    assert "lineage" not in payload["items"][0]
    assert "image_url" in payload["items"][0]


def test_destination_slug_not_dropped_and_city_slug_legacy_still_works_new(client, db_session, city_factory):
    city, dest, _ = destination_with_scope(db_session, city_factory, slug="compat-dest")
    normalized = normalize_place_query_params(PlaceQueryParams(destination_slug=dest.slug, limit=10, offset=0, sort_by="title", sort_order="asc"))
    assert normalized.destination_slug == dest.slug
    assert client.get("/places/", params={"city_slug": city.slug}).status_code == 200


def test_service_only_does_not_leak_to_destination_catalog_new(client, db_session, city_factory, monkeypatch):
    monkeypatch.setattr("services.destination_flags.destination_catalog_reads_enabled", lambda: True)
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="hidden-catalog")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    titles = [item["title"] for item in client.get("/places/", params={"destination_slug": dest.slug}).json()["items"]]
    assert not any("Остановка" in title for title in titles)
