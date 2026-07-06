from __future__ import annotations

from models.destination import Destination, DestinationScope


def _candidate_body(**overrides):
    base = {
        "candidate_key": "relation:9001",
        "title": "Куршская коса",
        "display_name": "Куршская коса, Калининградская область",
        "lat": 55.17,
        "lng": 20.86,
        "bbox": {"south": 54.94, "west": 20.43, "north": 55.32, "east": 20.99},
        "osm_type": "relation",
        "osm_id": 9001,
        "destination_type": "tourist_cluster",
        "import_strategy": "osm_relation",
    }
    base.update(overrides)
    return {"candidate": base}


def test_admin_destination_geo_search_new(client, monkeypatch):
    monkeypatch.setenv("CITYGO_DESTINATION_GEO_ADAPTER", "deterministic")
    response = client.get("/admin/destinations/geo-search", params={"q": "куршская"})
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "куршская"
    assert len(body["items"]) >= 1
    assert body["items"][0]["candidate_key"] == "relation:9001"


def test_admin_create_destination_from_geo_candidate_new(client, db_session):
    response = client.post(
        "/admin/destinations/from-geo-candidate",
        json=_candidate_body() | {"slug": "geo-kursh", "name": "Куршская коса"},
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "geo-kursh"
    assert db_session.query(Destination).filter_by(slug="geo-kursh").count() == 1


def test_admin_create_destination_from_geo_candidate_duplicate_slug_new(client):
    payload = _candidate_body() | {"slug": "geo-dup", "name": "Дубликат"}
    assert client.post("/admin/destinations/from-geo-candidate", json=payload).status_code == 200
    assert client.post("/admin/destinations/from-geo-candidate", json=payload).status_code == 409


def test_admin_scope_from_geo_candidate_create_new(client, db_session):
    dest = client.post("/admin/destinations", json={"slug": "geo-scope-dest", "name": "Geo Dest"}).json()
    response = client.post(
        f"/admin/destinations/{dest['slug']}/scopes/from-geo-candidate",
        json=_candidate_body() | {"code": "geo-core", "name": "Основной"},
    )
    assert response.status_code == 200
    assert response.json()["action"] == "created"
    destination = db_session.query(Destination).filter_by(slug="geo-scope-dest").one()
    assert db_session.query(DestinationScope).filter_by(destination_id=destination.id, code="geo-core").count() == 1


def test_admin_scope_from_geo_candidate_recovers_existing_new(client, db_session):
    dest = client.post("/admin/destinations", json={"slug": "geo-recover", "name": "Recover"}).json()
    first = client.post(
        f"/admin/destinations/{dest['slug']}/scopes/from-geo-candidate",
        json=_candidate_body() | {"code": "shared", "name": "Первый"},
    )
    assert first.json()["action"] == "created"
    second = client.post(
        f"/admin/destinations/{dest['slug']}/scopes/from-geo-candidate",
        json=_candidate_body(bbox={"south": 54.0, "west": 20.0, "north": 55.5, "east": 21.5})
        | {"code": "shared", "name": "Обновлённый", "recover": True},
    )
    assert second.status_code == 200
    assert second.json()["action"] == "recovered"
    destination = db_session.query(Destination).filter_by(slug="geo-recover").one()
    scope = db_session.query(DestinationScope).filter_by(destination_id=destination.id, code="shared").one()
    assert scope.name == "Обновлённый"
    assert scope.bbox["north"] == 55.5


def test_geo_search_compatible_with_pipeline_readiness_new(client, monkeypatch):
    monkeypatch.setenv("CITYGO_DESTINATION_GEO_ADAPTER", "deterministic")
    created = client.post(
        "/admin/destinations/from-geo-candidate",
        json=_candidate_body() | {"slug": "geo-ready", "name": "Готово"},
    ).json()
    client.post(
        f"/admin/destinations/{created['slug']}/scopes/from-geo-candidate",
        json=_candidate_body() | {"code": "core", "name": "Контур"},
    )
    readiness = client.get(f"/admin/destinations/{created['slug']}/readiness").json()
    assert readiness["bootstrap_ready"] is True
    assert readiness["bootstrap_blockers"] == []
