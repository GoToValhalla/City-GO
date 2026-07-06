from __future__ import annotations

from models.destination import Destination, DestinationScope
from models.destination_discovery import DestinationDiscoveryCandidate, DestinationDiscoveryJob


def test_discovery_region_search_cyrillic_and_latin_new(client, monkeypatch):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    ru = client.get("/admin/discovery/regions/search", params={"q": "Калининградская область"})
    en = client.get("/admin/discovery/regions/search", params={"q": "Kaliningrad Oblast"})
    assert ru.status_code == 200
    assert en.status_code == 200
    assert ru.json()["items"][0]["id"] == "test:RU-KGD"
    assert ru.json()["items"][0]["english_name"] == "Kaliningrad Oblast"


def test_discovery_kaliningrad_oblast_candidates_new(client, monkeypatch, db_session):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    before_dest = db_session.query(Destination).count()
    before_scopes = db_session.query(DestinationScope).count()
    response = client.post(
        "/admin/discovery/regions/test:RU-KGD/discover",
        json={"provider": "deterministic", "options": {"max_candidates": 100}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["job"]["status"] == "completed"
    assert body["preview"]["total_candidates"] == 6
    names = {item["name"] for item in body["preview"]["candidates"]}
    assert names == {"Калининград", "Зеленоградск", "Светлогорск", "Балтийск", "Янтарный", "Черняховск"}
    assert db_session.query(Destination).count() == before_dest
    assert db_session.query(DestinationScope).count() == before_scopes
    warning_codes = {w["code"] for c in body["preview"]["candidates"] for w in c["warnings"]}
    assert "POI_SIGNAL_UNAVAILABLE" in warning_codes
    assert "BORDER_BUFFER_RISK" in warning_codes or any(c["name"] == "Балтийск" for c in body["preview"]["candidates"])


def test_discovery_recommended_scopes_and_existing_match_new(client, monkeypatch, db_session):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    db_session.add(Destination(slug="zelenogradsk", name="Зеленоградск", destination_type="city"))
    db_session.commit()
    response = client.post("/admin/discovery/regions/test:RU-KGD/discover", json={"provider": "deterministic"})
    candidate = next(c for c in response.json()["preview"]["candidates"] if c["name"] == "Зеленоградск")
    assert candidate["existing_match"]["slug"] == "zelenogradsk"
    assert candidate["recommended_scopes"]
    assert candidate["recommended_scopes"][0]["code"] == "city_core"


def test_discovery_bulk_create_idempotent_new(client, monkeypatch, db_session):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    discover = client.post("/admin/discovery/regions/test:RU-KGD/discover", json={"provider": "deterministic"})
    job_id = discover.json()["job"]["id"]
    candidate_id = next(c["id"] for c in discover.json()["preview"]["candidates"] if c["name"] == "Янтарный")
    payload = {"candidate_ids": [candidate_id], "options": {"update_existing_scopes": False}}
    first = client.post(f"/admin/discovery/jobs/{job_id}/bulk-create", json=payload)
    second = client.post(f"/admin/discovery/jobs/{job_id}/bulk-create", json=payload)
    assert first.status_code == 200
    assert first.json()["created"] == 1
    assert second.status_code == 200
    assert second.json()["skipped_existing"] == 1
    assert db_session.query(Destination).filter_by(slug="yantarny").count() == 1
    assert db_session.query(DestinationScope).filter(DestinationScope.code == "city_core").count() >= 1


def test_discovery_bulk_create_skips_existing_destination_new(client, monkeypatch, db_session):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    db_session.add(Destination(slug="zelenogradsk", name="Зеленоградск", destination_type="city"))
    db_session.commit()
    discover = client.post("/admin/discovery/regions/test:RU-KGD/discover", json={"provider": "deterministic"})
    job_id = discover.json()["job"]["id"]
    candidate_id = next(c["id"] for c in discover.json()["preview"]["candidates"] if c["name"] == "Зеленоградск")
    result = client.post(f"/admin/discovery/jobs/{job_id}/bulk-create", json={"candidate_ids": [candidate_id]})
    assert result.json()["skipped_existing"] == 1
    assert db_session.query(Destination).filter_by(slug="zelenogradsk").count() == 1


def test_discovery_update_existing_scopes_only_when_explicit_new(client, monkeypatch, db_session):
    monkeypatch.setenv("CITYGO_DISCOVERY_PROVIDER", "deterministic")
    dest = Destination(slug="baltiysk", name="Балтийск", destination_type="city")
    db_session.add(dest)
    db_session.flush()
    db_session.add(DestinationScope(destination_id=dest.id, code="city_core", name="Старое", scope_type="catalog", import_strategy="single_bbox", import_profile="tourist_core"))
    db_session.commit()
    discover = client.post("/admin/discovery/regions/test:RU-KGD/discover", json={"provider": "deterministic"})
    job_id = discover.json()["job"]["id"]
    candidate_id = next(c["id"] for c in discover.json()["preview"]["candidates"] if c["name"] == "Балтийск")
    without = client.post(f"/admin/discovery/jobs/{job_id}/bulk-create", json={"candidate_ids": [candidate_id], "options": {"update_existing_scopes": False}})
    assert without.json()["skipped_existing"] == 1
    scope = db_session.query(DestinationScope).filter_by(destination_id=dest.id, code="city_core").one()
    assert scope.name == "Старое"
    with_update = client.post(
        f"/admin/discovery/jobs/{job_id}/bulk-create",
        json={"candidate_ids": [candidate_id], "options": {"update_existing_scopes": True}},
    )
    assert with_update.json()["created"] == 1
    db_session.refresh(scope)
    assert scope.name != "Старое"


def test_existing_geo_search_endpoints_still_work_new(client, monkeypatch):
    monkeypatch.setenv("CITYGO_DESTINATION_GEO_ADAPTER", "deterministic")
    assert client.get("/admin/destinations/geo-search", params={"q": "куршская"}).status_code == 200
