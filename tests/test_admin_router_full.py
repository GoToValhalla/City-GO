from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from models.route import Route


def test_admin_dashboard_returns_counts(client, place_factory):
    place_factory(title="Опубликованное место")

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cities_total"] >= 1
    assert payload["places_total"] >= 1
    assert "pending_photos" in payload
    assert "audit_events_total" in payload


def test_admin_city_import_creates_city_and_import_job(client, db_session, monkeypatch):
    from models.city_admin_import_job import CityAdminImportJob
    from models.city_import_scope import CityImportScope

    response = client.post(
        "/admin/cities/import",
        json={
            "name": "Светлогорск",
            "country": "Россия",
            "region": "Калининградская область",
            "center_lat": 54.94,
            "center_lng": 20.16,
            "radius_km": 10,
            "actor": "qa",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["city_name"] == "Светлогорск"
    assert payload["job_status"] == "queued"

    jobs_response = client.get("/admin/import-jobs")
    assert jobs_response.status_code == 200
    assert jobs_response.json()["total"] >= 1

    scopes = db_session.query(CityImportScope).filter_by(city_id=payload["city_id"]).all()
    assert len(scopes) == 2
    assert {scope.code for scope in scopes} == {"tourist_core", "food_area"}
    assert all(scope.enabled for scope in scopes)
    jobs = db_session.query(CityAdminImportJob).filter_by(city_id=payload["city_id"]).all()
    assert len(jobs) == 1
    assert jobs[0].status == "queued"


def test_admin_place_publish_unpublish_and_audit(client, place_factory):
    place = place_factory(title="Место для публикации")

    publish_response = client.post(
        f"/admin/places/{place.id}/publish",
        json={"actor": "editor", "reason": "Проверено"},
    )
    assert publish_response.status_code == 200
    assert publish_response.json()["is_published"] is True
    assert publish_response.json()["is_visible_in_catalog"] is True
    assert publish_response.json()["is_route_eligible"] is True

    unpublish_response = client.post(
        f"/admin/places/{place.id}/unpublish",
        json={"actor": "editor", "reason": "Временно скрыто"},
    )
    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["is_published"] is False
    assert unpublish_response.json()["publication_status"] == "unpublished"

    audit_response = client.get("/admin/audit-log", params={"entity_type": "place"})
    assert audit_response.status_code == 200
    actions = [item["action"] for item in audit_response.json()["items"]]
    assert "publish_place" in actions
    assert "unpublish_place" in actions


def test_admin_manual_place_image_goes_to_review_queue(client, place_factory):
    place = place_factory(title="Место с ручным фото")

    response = client.post(
        "/admin/place-images",
        json={
            "place_id": place.id,
            "image_url": "https://example.com/manual.jpg",
            "source_type": "manual_upload",
            "confidence": 0.8,
            "actor": "moderator",
            "comment": "Ручная загрузка",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["place_id"] == place.id
    assert payload["status"] == PLACE_IMAGE_STATUS_NEEDS_REVIEW

    pending_response = client.get("/admin/place-images/pending")
    assert pending_response.status_code == 200
    assert any(item["image_id"] == payload["id"] for item in pending_response.json()["items"])


def test_admin_route_create_update_points_and_unpublish(client, db_session, city_factory, place_factory):
    city = city_factory(slug="admin-route-city", name="Город маршрутов")
    first_place = place_factory(slug="admin-route-place-1", title="Первая точка", city_id=city.id)
    second_place = place_factory(slug="admin-route-place-2", title="Вторая точка", city_id=city.id)

    create_response = client.post(
        "/admin/routes",
        json={
            "city_id": city.id,
            "slug": "admin-test-route",
            "title": "Тестовый маршрут",
            "route_mode": "walk",
            "is_active": False,
            "actor": "editor",
        },
    )
    assert create_response.status_code == 200
    route_id = create_response.json()["id"]

    points_response = client.put(
        f"/admin/routes/{route_id}/points",
        json={
            "actor": "editor",
            "reason": "Собрали маршрут руками",
            "points": [
                {"place_id": first_place.id, "position": 1},
                {"place_id": second_place.id, "position": 2},
            ],
        },
    )
    assert points_response.status_code == 200
    assert len(points_response.json()["points"]) == 2

    publish_response = client.post(f"/admin/routes/{route_id}/publish", json={"actor": "editor"})
    assert publish_response.status_code == 200
    assert publish_response.json()["is_active"] is True

    unpublish_response = client.post(
        f"/admin/routes/{route_id}/unpublish",
        json={"actor": "editor", "reason": "Снять с публикации"},
    )
    assert unpublish_response.status_code == 200
    assert unpublish_response.json()["is_active"] is False
