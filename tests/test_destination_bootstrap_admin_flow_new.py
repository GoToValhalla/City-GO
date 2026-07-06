from __future__ import annotations

from models.destination import Destination, DestinationPlaceMembership, DestinationScope
from models.destination_data_pipeline import DestinationDataPipelineRun


def test_admin_destination_create_update_and_duplicate_slug_new(client):
    body = {"slug": " Test Destination ", "name": "Тестовое направление", "destination_type": "tourist_cluster", "center_lat": 54.7, "center_lng": 20.5}
    created = client.post("/admin/destinations", json=body)
    assert created.status_code == 200
    assert created.json()["slug"] == "test-destination"
    duplicate = client.post("/admin/destinations", json=body)
    assert duplicate.status_code == 409
    updated = client.patch("/admin/destinations/test-destination", json={"name": "Новое название"})
    assert updated.status_code == 200
    assert updated.json()["title"] == "Новое название"


def test_admin_destination_rejects_invalid_coordinates_new(client):
    response = client.post("/admin/destinations", json={"slug": "bad-coords", "name": "Bad", "center_lat": 100})
    assert response.status_code == 422


def test_admin_scope_crud_and_delete_guard_new(client, db_session):
    dest = client.post("/admin/destinations", json={"slug": "scope-crud", "name": "Контуры"}).json()
    scope = client.post(f"/admin/destinations/{dest['slug']}/scopes", json=_scope_body("core"))
    assert scope.status_code == 200
    scope_id = scope.json()["id"]
    patched = client.patch(f"/admin/destinations/{dest['slug']}/scopes/{scope_id}", json={"name": "Новый контур", "bbox": _bbox(north=55.2)})
    assert patched.status_code == 200
    assert patched.json()["name"] == "Новый контур"
    destination = db_session.query(Destination).filter_by(slug="scope-crud").one()
    db_session.add(DestinationDataPipelineRun(destination_id=destination.id, triggered_by="test", status="running", stage="importing", scope_ids=[scope_id], counters={}, errors=[], mode="full"))
    db_session.commit()
    blocked = client.delete(f"/admin/destinations/{dest['slug']}/scopes/{scope_id}")
    assert blocked.status_code == 409


def test_bootstrap_readiness_blocks_empty_and_invalid_scopes_new(client, db_session):
    dest = client.post("/admin/destinations", json={"slug": "bootstrap-empty", "name": "Пустое"}).json()
    empty = client.get(f"/admin/destinations/{dest['slug']}/readiness").json()
    assert empty["bootstrap_ready"] is False
    assert empty["bootstrap_blockers"] == ["NO_SCOPES"]
    destination = db_session.query(Destination).filter_by(slug="bootstrap-empty").one()
    db_session.add(DestinationScope(destination_id=destination.id, code="bad", name="Bad", bbox={"south": 2, "north": 1, "west": 0, "east": 1}, enabled=True))
    db_session.commit()
    invalid = client.get(f"/admin/destinations/{dest['slug']}/readiness").json()
    assert invalid["bootstrap_blockers"] == ["INVALID_SCOPE_GEOMETRY"]


def test_admin_places_can_filter_by_destination_slug_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="dest-filter-city")
    kept = place_factory(city_id=city.id, slug="kept-place", title="Нужное место")
    other = place_factory(city_id=city.id, slug="other-place", title="Другое место")
    dest = Destination(slug="dest-filter", name="Фильтр", destination_type="tourist_cluster", is_active=True)
    db_session.add(dest)
    db_session.flush()
    db_session.add(DestinationPlaceMembership(place_id=kept.id, destination_id=dest.id, is_hidden=False))
    db_session.add(DestinationPlaceMembership(place_id=other.id, destination_id=dest.id, is_hidden=True))
    db_session.commit()
    response = client.get("/admin/places/search", params={"destination_slug": "dest-filter"})
    titles = [item["title"] for item in response.json()["items"]]
    assert titles == ["Нужное место"]


def _scope_body(code: str) -> dict[str, object]:
    return {"code": code, "name": "Основной", "bbox": _bbox(), "import_profile": "tourist_core"}


def _bbox(*, north: float = 55.0) -> dict[str, float]:
    return {"south": 54.5, "west": 20.0, "north": north, "east": 21.0}
