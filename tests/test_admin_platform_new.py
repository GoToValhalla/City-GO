from models.product_event import ProductEvent
from models.system_log import SystemLog


def test_admin_platform_endpoints_are_registered_new(client):
    for path in ("/admin/quality", "/admin/system-health", "/admin/analytics"):
        assert client.get(path).status_code == 200


def test_quality_and_analytics_use_real_rows_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="platform-city", name="Платформа")
    place_factory(city_id=city.id)
    db_session.add(ProductEvent(
        event_type="place_viewed", city_slug=city.slug,
        user_id="u-1", payload={"channel": "web"},
    ))
    db_session.commit()

    quality = client.get(f"/admin/quality?city_slug={city.slug}").json()
    analytics = client.get(f"/admin/analytics?city_slug={city.slug}&channel=web").json()

    assert quality["items"][0]["city_slug"] == city.slug
    assert analytics["metrics"]["active_users"] == 1
    assert analytics["metrics"]["place_views"] == 1


def test_quality_uses_live_score_when_stored_readiness_is_zero_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="live-quality-city", name="Live Quality")
    city.readiness_score = 0
    db_session.add(city)
    place_factory(
        city_id=city.id,
        image_url="https://example.com/photo.jpg",
        address="Main street 1",
    )
    db_session.commit()

    row = client.get(f"/admin/quality?city_slug={city.slug}").json()["items"][0]

    assert row["readiness_score"] == 100
    assert row["stored_readiness_score"] == 0
    assert row["primary_blocker"] is None


def test_alert_lifecycle_is_idempotent_new(client, db_session):
    log = SystemLog(level="error", module="import", message="boom", request_id="req-1")
    db_session.add(log)
    db_session.commit()

    first = client.post(f"/admin/system-health/alerts/{log.id}", json={"status": "acknowledged"})
    second = client.post(f"/admin/system-health/alerts/{log.id}", json={"status": "acknowledged"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["status"] == "acknowledged"
    assert client.get("/admin/system-health/alerts?status=acknowledged").json()["total"] == 1


def test_workspace_contains_operational_summary_new(client, city_factory):
    city = city_factory(slug="workspace-platform")
    payload = client.get(f"/admin/cities/by-slug/{city.slug}/workspace").json()
    assert "quality" in payload["operations"]
    assert "routes" in payload["operations"]


def test_workspace_readiness_uses_live_quality_score_new(client, db_session, city_factory, place_factory):
    city = city_factory(slug="workspace-live-quality")
    city.readiness_score = 0
    db_session.add(city)
    place_factory(
        city_id=city.id,
        image_url="https://example.com/photo.jpg",
        address="Main street 1",
    )
    db_session.commit()

    payload = client.get(f"/admin/cities/by-slug/{city.slug}/workspace").json()

    assert payload["readiness"]["readiness_score"] == 100
    assert payload["readiness"]["stored_readiness_score"] == 0
    assert payload["readiness"]["primary_blocker"] is None