"""Тесты Route Operations API."""

from __future__ import annotations


def test_eligibility_list_excludes_pharmacy_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-elig-city")
    place_factory(slug="ops-cafe", category="cafe", city_id=city.id)
    place_factory(slug="ops-pharm", category="pharmacy", city_id=city.id)
    response = client.get(f"/admin/routes/eligibility?city_slug={city.slug}&eligible=false")
    assert response.status_code == 200
    body = response.json()
    categories = {row["category"] for row in body["items"]}
    assert "pharmacy" in categories
    assert all(not row["eligible"] for row in body["items"])


def test_data_quality_report_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-dq-city")
    place_factory(slug="dq-cafe", category="cafe", city_id=city.id)
    place_factory(slug="dq-pharm", category="pharmacy", city_id=city.id)
    response = client.get(f"/admin/routes/data-quality/{city.slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["places_total"] >= 2
    assert body["suspicious_category_counts"].get("pharmacy", 0) >= 1
    assert any(i["code"] == "no_photo" for i in body["issues"])


def test_data_quality_report_includes_p0_action_plan_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-dq-action-plan")
    place_factory(slug="dq-action-cafe", category="cafe", city_id=city.id, address="")
    place_factory(slug="dq-action-pharmacy", category="pharmacy", city_id=city.id, address="")

    response = client.get(f"/admin/routes/data-quality/{city.slug}")

    assert response.status_code == 200
    body = response.json()
    codes = {item["code"] for item in body["action_plan"]}
    assert "low_route_eligible_count" in codes
    assert "review_suspicious_categories" in codes
    assert "run_address_recovery" in codes
    assert "run_image_enrichment" in codes
    assert "run_description_enrichment" in codes
    assert all(item["admin_link"].startswith(f"/admin/routes/eligibility?city_slug={city.slug}") for item in body["action_plan"])


def test_city_readiness_empty_city_new(client, city_factory) -> None:
    city = city_factory(slug="ops-ready-empty")
    response = client.get(f"/admin/routes/readiness/{city.slug}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["readiness_score"] == 0


def test_city_readiness_with_places_new(client, city_factory, place_factory) -> None:
    city = city_factory(slug="ops-ready-ok")
    place_factory(slug="rdy-museum", category="museum", city_id=city.id,
                  lat=city.center_lat, lng=city.center_lng)
    response = client.get(f"/admin/routes/readiness/{city.slug}")
    assert response.status_code == 200
    assert response.json()["components"]["places_total"] >= 1


def test_readiness_list_new(client, city_factory) -> None:
    city_factory(slug="ops-list-a")
    city_factory(slug="ops-list-b")
    response = client.get("/admin/routes/readiness")
    assert response.status_code == 200
    slugs = {row["city_slug"] for row in response.json()["items"]}
    assert "ops-list-a" in slugs
